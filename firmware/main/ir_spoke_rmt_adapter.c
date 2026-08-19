#include "ir_spoke_rmt_adapter.h"

#include <inttypes.h>

#include "driver/rmt_encoder.h"
#include "driver/rmt_rx.h"
#include "driver/rmt_tx.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "ir_spoke_ble_csc.h"
#include "ir_spoke_debug.h"

#define RX_SYMBOL_COUNT 128

typedef struct {
    uint64_t timestamp_us;
    uint32_t duration_us;
} blockage_event_t;

static rmt_channel_handle_t tx_channel;
static rmt_channel_handle_t rx_channel;
static rmt_encoder_handle_t tx_encoder;
static rmt_symbol_word_t rx_symbols[RX_SYMBOL_COUNT];
static QueueHandle_t event_queue;
static TaskHandle_t receive_task;
static ir_spoke_pipeline_t *target_pipeline;
static ir_spoke_can_publisher_t *can_publisher;
static uint32_t capture_resolution_hz;
static ir_spoke_runtime_config_t runtime_config;
static volatile uint32_t rx_capture_count;
static volatile uint32_t rx_queue_drops;
static volatile uint32_t rx_last_symbol_count;

static uint32_t ticks_to_us(uint32_t ticks) {
    return (uint32_t)(((uint64_t)ticks * 1000000u +
                      capture_resolution_hz / 2u) / capture_resolution_hz);
}

static bool rx_done(rmt_channel_handle_t channel,
                    const rmt_rx_done_event_data_t *data, void *context) {
    (void)channel;
    (void)context;
    BaseType_t wake = pdFALSE;
    const uint64_t now = (uint64_t)esp_timer_get_time();
    uint64_t captured_us = 0;
    for (size_t i = 0; i < data->num_symbols; ++i) {
        captured_us += ticks_to_us(data->received_symbols[i].duration0);
        captured_us += ticks_to_us(data->received_symbols[i].duration1);
    }
    uint64_t cursor_us = now > captured_us ? now - captured_us : 0;
    for (size_t i = 0; i < data->num_symbols; ++i) {
        const rmt_symbol_word_t s = data->received_symbols[i];
        const blockage_event_t phases[2] = {
            {.timestamp_us = cursor_us,
             .duration_us = s.level0 ? 0u : ticks_to_us(s.duration0)},
            {.timestamp_us = cursor_us + ticks_to_us(s.duration0),
             .duration_us = s.level1 ? 0u : ticks_to_us(s.duration1)},
        };
        for (unsigned phase = 0; phase < 2; ++phase) {
            if (phases[phase].duration_us &&
                xQueueSendFromISR(event_queue, &phases[phase], &wake) != pdTRUE) {
                ++rx_queue_drops;
            }
        }
        cursor_us += ticks_to_us(s.duration0) + ticks_to_us(s.duration1);
    }
    rx_last_symbol_count = (uint32_t)data->num_symbols;
    ++rx_capture_count;
    vTaskNotifyGiveFromISR(receive_task, &wake);
    return wake == pdTRUE;
}

static void receive_loop(void *argument) {
    const ir_spoke_runtime_config_t *config =
        (const ir_spoke_runtime_config_t *)argument;
    const rmt_receive_config_t receive_config = {
        .signal_range_min_ns = config->rx_glitch_filter_us * 1000u,
        .signal_range_max_ns = config->link_loss_us * 1000u,
    };
    uint32_t reported_queue_drops = 0;

    ir_spoke_debug_event(
        IR_SPOKE_DEBUG_RMT,
        "RX task started min_signal=%luns max_signal=%luns",
        (unsigned long)receive_config.signal_range_min_ns,
        (unsigned long)receive_config.signal_range_max_ns);

    for (;;) {
        const esp_err_t receive_result = rmt_receive(
            rx_channel, rx_symbols, sizeof(rx_symbols), &receive_config);
        if (receive_result != ESP_OK) {
            ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                                 "rmt_receive failed: %s",
                                 esp_err_to_name(receive_result));
            ESP_ERROR_CHECK(receive_result);
        }
        (void)ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        const uint32_t capture_count = rx_capture_count;
        const uint32_t symbols = rx_last_symbol_count;
        const uint32_t drops = rx_queue_drops;
        ir_spoke_debug_event(
            IR_SPOKE_DEBUG_RMT_CAPTURE,
            "capture=%" PRIu32 " symbols=%" PRIu32 " queue_drops=%" PRIu32,
            capture_count, symbols, drops);
        if (drops != reported_queue_drops) {
            ir_spoke_debug_event(
                IR_SPOKE_DEBUG_ERROR,
                "RMT event queue overflow: total_drops=%" PRIu32
                " new_drops=%" PRIu32,
                drops, drops - reported_queue_drops);
            reported_queue_drops = drops;
        }

        blockage_event_t event;
        while (xQueueReceive(event_queue, &event, 0) == pdTRUE) {
            const bool was_locked =
                target_pipeline->pattern.estimate.count_locked;
            const uint8_t previous_spoke =
                target_pipeline->pattern.estimate.current_spoke;
            const ir_spoke_pulse_result_t result =
                ir_spoke_pipeline_ingest(target_pipeline,
                    event.timestamp_us, event.duration_us);
            const ir_spoke_estimate_t *estimate =
                ir_spoke_pattern_estimate(&target_pipeline->pattern);

            if (result == IR_SPOKE_PULSE_ACCEPTED) {
                ir_spoke_debug_event(
                    IR_SPOKE_DEBUG_PULSE_ACCEPTED,
                    "t=%" PRIu64 "us duration=%" PRIu32
                    "us accepted=%" PRIu32 " spoke=%u/%u locked=%s conf=%.3f",
                    event.timestamp_us,
                    event.duration_us,
                    target_pipeline->detector.accepted,
                    estimate ? estimate->current_spoke : 0,
                    estimate ? estimate->spoke_count : 0,
                    estimate && estimate->count_locked ? "yes" : "no",
                    estimate ? (double)estimate->confidence : 0.0);
            } else {
                const char *reason = result == IR_SPOKE_PULSE_REJECT_SHORT
                                         ? "short"
                                         : "long";
                ir_spoke_debug_event(
                    IR_SPOKE_DEBUG_PULSE_REJECTED,
                    "t=%" PRIu64 "us duration=%" PRIu32
                    "us reason=%s rejected_short=%" PRIu32
                    " rejected_long=%" PRIu32,
                    event.timestamp_us,
                    event.duration_us,
                    reason,
                    target_pipeline->detector.rejected_short,
                    target_pipeline->detector.rejected_long);
            }

            if (estimate && was_locked != estimate->count_locked) {
                ir_spoke_debug_event(
                    IR_SPOKE_DEBUG_ESTIMATOR,
                    "%s spoke_count=%u confidence=%.3f accepted_events=%" PRIu32,
                    estimate->count_locked ? "LOCKED" : "UNLOCKED",
                    estimate->spoke_count,
                    (double)estimate->confidence,
                    target_pipeline->pattern.accepted_events);
            }

            if (result == IR_SPOKE_PULSE_ACCEPTED && can_publisher) {
                const int can_result = ir_spoke_can_publish_estimate(
                    can_publisher, estimate, event.duration_us);
                if (can_result == 0) {
                    ir_spoke_debug_event(
                        IR_SPOKE_DEBUG_CAN_TX,
                        "telemetry published spoke=%u/%u duration=%" PRIu32 "us",
                        estimate ? estimate->current_spoke : 0,
                        estimate ? estimate->spoke_count : 0,
                        event.duration_us);
                } else {
                    ir_spoke_debug_event(
                        IR_SPOKE_DEBUG_ERROR,
                        "CAN telemetry publish failed rc=%d", can_result);
                }
            }

            if (result == IR_SPOKE_PULSE_ACCEPTED && was_locked &&
                previous_spoke != 0 && estimate && estimate->count_locked &&
                estimate->current_spoke == 0) {
                ir_spoke_debug_event(
                    IR_SPOKE_DEBUG_REVOLUTION,
                    "wheel revolution t=%" PRIu64
                    "us spokes=%u period=%.0fus wheel_hz=%.3f",
                    event.timestamp_us,
                    estimate->spoke_count,
                    (double)estimate->revolution_period_us,
                    (double)estimate->wheel_hz);
                ir_spoke_ble_csc_on_wheel_revolution(event.timestamp_us);
            }
        }
    }
}

void ir_spoke_rmt_set_can_publisher(
    ir_spoke_can_publisher_t *publisher) {
    can_publisher = publisher;
}

int ir_spoke_rmt_start(const ir_spoke_runtime_config_t *config,
                       ir_spoke_pipeline_t *pipeline) {
    const int config_result = ir_spoke_config_validate(config);
    if (config_result || !pipeline) {
        ir_spoke_debug_event(
            IR_SPOKE_DEBUG_ERROR,
            "invalid RMT start arguments config_rc=%d pipeline=%s",
            config_result, pipeline ? "yes" : "no");
        return -1;
    }
    runtime_config = *config;
    config = &runtime_config;
    target_pipeline = pipeline;
    capture_resolution_hz = config->rmt_resolution_hz;
    event_queue = xQueueCreate(32, sizeof(blockage_event_t));
    if (!event_queue) {
        ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                             "failed to allocate RMT event queue");
        return -2;
    }

    ir_spoke_debug_event(
        IR_SPOKE_DEBUG_RMT,
        "initializing TX gpio=%ld RX gpio=%ld resolution=%luHz mem=%lu symbols",
        (long)config->tx_gpio,
        (long)config->rx_gpio,
        (unsigned long)config->rmt_resolution_hz,
        (unsigned long)config->rmt_mem_block_symbols);

    const rmt_tx_channel_config_t tx_cfg = {
        .gpio_num = config->tx_gpio,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = config->rmt_resolution_hz,
        .mem_block_symbols = config->rmt_mem_block_symbols,
        .trans_queue_depth = config->rmt_tx_queue_depth,
    };
    const rmt_rx_channel_config_t rx_cfg = {
        .gpio_num = config->rx_gpio,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = config->rmt_resolution_hz,
        .mem_block_symbols = config->rmt_mem_block_symbols,
    };
    ESP_RETURN_ON_ERROR(rmt_new_tx_channel(&tx_cfg, &tx_channel), "ir_rmt", "tx");
    ESP_RETURN_ON_ERROR(rmt_new_rx_channel(&rx_cfg, &rx_channel), "ir_rmt", "rx");
    ESP_RETURN_ON_ERROR(rmt_new_copy_encoder(
        &(rmt_copy_encoder_config_t){0}, &tx_encoder), "ir_rmt", "encoder");

    const rmt_carrier_config_t tx_carrier = {
        .frequency_hz = config->carrier_hz,
        .duty_cycle = config->carrier_duty,
        .flags = {.polarity_active_low = false, .always_on = true},
    };
    const rmt_carrier_config_t rx_carrier = {
        .frequency_hz = ir_spoke_config_rx_demod_hz(config),
        .duty_cycle = config->rx_demod_duty,
        .flags = {.polarity_active_low = false},
    };
    ESP_RETURN_ON_ERROR(rmt_apply_carrier(tx_channel, &tx_carrier),
                        "ir_rmt", "tx carrier");
    ESP_RETURN_ON_ERROR(rmt_apply_carrier(rx_channel, &rx_carrier),
                        "ir_rmt", "rx carrier");
    ESP_RETURN_ON_ERROR(rmt_rx_register_event_callbacks(
        rx_channel, &(rmt_rx_event_callbacks_t){.on_recv_done = rx_done}, 0),
        "ir_rmt", "callback");
    ESP_RETURN_ON_ERROR(rmt_enable(tx_channel), "ir_rmt", "enable tx");
    ESP_RETURN_ON_ERROR(rmt_enable(rx_channel), "ir_rmt", "enable rx");

    if (xTaskCreate(receive_loop, "ir_spoke_rx", 4096, (void *)config, 10,
                    &receive_task) != pdPASS) {
        ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                             "failed to create RMT receive task");
        return -3;
    }
    const rmt_symbol_word_t continuous_high = {
        .duration0 = 10000, .level0 = 1,
        .duration1 = 10000, .level1 = 1,
    };
    const rmt_transmit_config_t loop = {.loop_count = -1};
    ESP_RETURN_ON_ERROR(rmt_transmit(tx_channel, tx_encoder, &continuous_high,
        sizeof(continuous_high), &loop), "ir_rmt", "start carrier");

    ir_spoke_debug_event(
        IR_SPOKE_DEBUG_RMT,
        "READY tx_carrier=%luHz rx_demod=%luHz glitch_filter=%luus link_loss=%luus",
        (unsigned long)config->carrier_hz,
        (unsigned long)ir_spoke_config_rx_demod_hz(config),
        (unsigned long)config->rx_glitch_filter_us,
        (unsigned long)config->link_loss_us);
    return 0;
}
