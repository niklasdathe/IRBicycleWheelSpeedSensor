#include "ir_spoke_link_monitor.h"

#include <stdint.h>

#include "driver/pulse_cnt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ir_spoke_debug.h"
#include "sdkconfig.h"

#if defined(CONFIG_IR_SPOKE_DEBUG_ENABLE)
static pcnt_unit_handle_t link_unit;
static pcnt_channel_handle_t link_channel;
static ir_spoke_runtime_config_t link_config;

static void link_monitor_task(void *argument) {
    (void)argument;
    const uint32_t configured_sample_ms =
        (uint32_t)CONFIG_IR_SPOKE_DEBUG_LINK_SAMPLE_MS;
    const TickType_t delay_ticks = pdMS_TO_TICKS(configured_sample_ms);
    int64_t sample_start_us = esp_timer_get_time();

    ir_spoke_debug_carrier_link_state(
        IR_SPOKE_LINK_UNKNOWN, 0, link_config.carrier_hz, 0,
        configured_sample_ms);

    for (;;) {
        vTaskDelay(delay_ticks);

        int edge_count = 0;
        const esp_err_t read_rc = pcnt_unit_get_count(link_unit, &edge_count);
        const int64_t sample_end_us = esp_timer_get_time();
        const esp_err_t clear_rc = pcnt_unit_clear_count(link_unit);

        if (read_rc != ESP_OK || clear_rc != ESP_OK) {
            ir_spoke_debug_event(
                IR_SPOKE_DEBUG_ERROR,
                "optical-link PCNT sample failed read=%s clear=%s",
                esp_err_to_name(read_rc), esp_err_to_name(clear_rc));
            sample_start_us = sample_end_us;
            continue;
        }

        const uint64_t elapsed_us = sample_end_us > sample_start_us
                                        ? (uint64_t)(sample_end_us - sample_start_us)
                                        : (uint64_t)configured_sample_ms * 1000ULL;
        sample_start_us = sample_end_us;

        const uint32_t edges = edge_count > 0 ? (uint32_t)edge_count : 0u;
        const uint32_t measured_hz = elapsed_us
            ? (uint32_t)(((uint64_t)edges * 1000000ULL + elapsed_us / 2ULL) /
                         elapsed_us)
            : 0u;
        const uint32_t minimum_hz =
            (uint32_t)(((uint64_t)link_config.carrier_hz *
                        CONFIG_IR_SPOKE_DEBUG_LINK_MIN_CARRIER_PERCENT) /
                       100ULL);
        const ir_spoke_link_state_t state =
            measured_hz >= minimum_hz ? IR_SPOKE_LINK_UP
                                      : IR_SPOKE_LINK_DOWN;
        const uint32_t actual_sample_ms =
            (uint32_t)((elapsed_us + 500ULL) / 1000ULL);

        ir_spoke_debug_carrier_link_state(
            state, measured_hz, link_config.carrier_hz, edges,
            actual_sample_ms);
    }
}
#endif

esp_err_t ir_spoke_link_monitor_start(
    const ir_spoke_runtime_config_t *config) {
#if defined(CONFIG_IR_SPOKE_DEBUG_ENABLE)
    if (!config) return ESP_ERR_INVALID_ARG;
    link_config = *config;

    const pcnt_unit_config_t unit_config = {
        .low_limit = -1,
        .high_limit = 30000,
    };
    esp_err_t rc = pcnt_new_unit(&unit_config, &link_unit);
    if (rc != ESP_OK) return rc;

    const pcnt_chan_config_t channel_config = {
        .edge_gpio_num = config->rx_gpio,
        .level_gpio_num = -1,
        .virt_level_io_level = 1,
    };
    rc = pcnt_new_channel(link_unit, &channel_config, &link_channel);
    if (rc != ESP_OK) return rc;

    rc = pcnt_channel_set_edge_action(
        link_channel,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE,
        PCNT_CHANNEL_EDGE_ACTION_HOLD);
    if (rc != ESP_OK) return rc;

    const pcnt_glitch_filter_config_t filter_config = {
        .max_glitch_ns = 500,
    };
    rc = pcnt_unit_set_glitch_filter(link_unit, &filter_config);
    if (rc != ESP_OK) return rc;

    rc = pcnt_unit_enable(link_unit);
    if (rc != ESP_OK) return rc;
    rc = pcnt_unit_clear_count(link_unit);
    if (rc != ESP_OK) return rc;
    rc = pcnt_unit_start(link_unit);
    if (rc != ESP_OK) return rc;

    if (xTaskCreate(link_monitor_task, "ir_link_mon", 3072, NULL, 6, NULL) !=
        pdPASS) {
        return ESP_ERR_NO_MEM;
    }

    ir_spoke_debug_event(
        IR_SPOKE_DEBUG_LINK,
        "carrier monitor active gpio=%ld sample=%dms threshold=%d%% expected=%luHz",
        (long)config->rx_gpio,
        CONFIG_IR_SPOKE_DEBUG_LINK_SAMPLE_MS,
        CONFIG_IR_SPOKE_DEBUG_LINK_MIN_CARRIER_PERCENT,
        (unsigned long)config->carrier_hz);
#else
    (void)config;
#endif
    return ESP_OK;
}
