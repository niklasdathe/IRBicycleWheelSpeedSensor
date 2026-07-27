#include "ir_spoke_rmt_adapter.h"

#include "driver/rmt_encoder.h"
#include "driver/rmt_rx.h"
#include "driver/rmt_tx.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#define IR_TX_GPIO 1
#define IR_RX_GPIO 2
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

static bool rx_done(rmt_channel_handle_t channel,
                    const rmt_rx_done_event_data_t *data, void *context) {
    (void)channel;
    (void)context;
    BaseType_t wake = pdFALSE;
    const uint64_t now = (uint64_t)esp_timer_get_time();
    for (size_t i = 0; i < data->num_symbols; ++i) {
        const rmt_symbol_word_t s = data->received_symbols[i];
        const blockage_event_t phases[2] = {
            {.timestamp_us = now, .duration_us = s.level0 ? 0u : s.duration0},
            {.timestamp_us = now, .duration_us = s.level1 ? 0u : s.duration1},
        };
        for (unsigned phase = 0; phase < 2; ++phase) {
            if (phases[phase].duration_us)
                (void)xQueueSendFromISR(event_queue, &phases[phase], &wake);
        }
    }
    vTaskNotifyGiveFromISR(receive_task, &wake);
    return wake == pdTRUE;
}

static void receive_loop(void *argument) {
    const ir_spoke_runtime_config_t *config =
        (const ir_spoke_runtime_config_t *)argument;
    const rmt_receive_config_t receive_config = {
        .signal_range_min_ns = IR_SPOKE_GLITCH_FILTER_US * 1000u,
        .signal_range_max_ns = config->link_loss_us * 1000u,
    };
    for (;;) {
        ESP_ERROR_CHECK(rmt_receive(rx_channel, rx_symbols,
            sizeof(rx_symbols), &receive_config));
        (void)ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        blockage_event_t event;
        while (xQueueReceive(event_queue, &event, 0) == pdTRUE) {
            (void)ir_spoke_pipeline_ingest(target_pipeline,
                event.timestamp_us, event.duration_us);
        }
    }
}

int ir_spoke_rmt_start(const ir_spoke_runtime_config_t *config,
                       ir_spoke_pipeline_t *pipeline) {
    if (ir_spoke_config_validate(config) || !pipeline) return -1;
    target_pipeline = pipeline;
    event_queue = xQueueCreate(32, sizeof(blockage_event_t));
    if (!event_queue) return -2;

    const rmt_tx_channel_config_t tx_cfg = {
        .gpio_num = IR_TX_GPIO,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = IR_SPOKE_RMT_RESOLUTION_HZ,
        .mem_block_symbols = 64,
        .trans_queue_depth = 2,
    };
    const rmt_rx_channel_config_t rx_cfg = {
        .gpio_num = IR_RX_GPIO,
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = IR_SPOKE_RMT_RESOLUTION_HZ,
        .mem_block_symbols = 64,
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
        .duty_cycle = 0.5f,
        .flags = {.polarity_active_low = false},
    };
    ESP_RETURN_ON_ERROR(rmt_apply_carrier(tx_channel, &tx_carrier), "ir_rmt", "tx carrier");
    ESP_RETURN_ON_ERROR(rmt_apply_carrier(rx_channel, &rx_carrier), "ir_rmt", "rx carrier");
    ESP_RETURN_ON_ERROR(rmt_rx_register_event_callbacks(rx_channel,
        &(rmt_rx_event_callbacks_t){.on_recv_done = rx_done}, 0), "ir_rmt", "callback");
    ESP_RETURN_ON_ERROR(rmt_enable(tx_channel), "ir_rmt", "enable tx");
    ESP_RETURN_ON_ERROR(rmt_enable(rx_channel), "ir_rmt", "enable rx");

    xTaskCreate(receive_loop, "ir_spoke_rx", 4096, (void *)config, 10,
                &receive_task);
    const rmt_symbol_word_t continuous_high = {
        .duration0 = 10000, .level0 = 1,
        .duration1 = 10000, .level1 = 1,
    };
    const rmt_transmit_config_t loop = {.loop_count = -1};
    ESP_RETURN_ON_ERROR(rmt_transmit(tx_channel, tx_encoder, &continuous_high,
        sizeof(continuous_high), &loop), "ir_rmt", "start carrier");
    return 0;
}
