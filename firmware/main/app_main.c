#include "esp_check.h"
#include "esp_log.h"
#include "ir_spoke_ble_csc.h"
#include "ir_spoke_can.h"
#include "ir_spoke_can_mcp2515_adapter.h"
#include "ir_spoke_config.h"
#include "ir_spoke_debug.h"
#include "ir_spoke_link_monitor.h"
#include "ir_spoke_pipeline.h"
#include "ir_spoke_rmt_adapter.h"

static ir_spoke_runtime_config_t runtime_config;
static ir_spoke_pipeline_t pipeline;
static ir_spoke_can_publisher_t can_publisher;

void app_main(void) {
    const esp_err_t debug_result = ir_spoke_debug_init();
    if (debug_result != ESP_OK) {
        ESP_LOGW("ir_spoke", "debug initialization failed: %s",
                 esp_err_to_name(debug_result));
    }

    ir_spoke_debug_event(IR_SPOKE_DEBUG_STARTUP,
                         "application starting");
    ir_spoke_config_defaults(&runtime_config);
    /* Application code may change carrier_hz before start, within the
       generated analog-compatible bounds. */
    ir_spoke_debug_event(
        IR_SPOKE_DEBUG_STARTUP,
        "config tx_gpio=%ld rx_gpio=%ld carrier=%luHz demod=%luHz "
        "rmt=%luHz glitch=%luus pulse=%lu..%luus link_loss=%luus",
        (long)runtime_config.tx_gpio,
        (long)runtime_config.rx_gpio,
        (unsigned long)runtime_config.carrier_hz,
        (unsigned long)ir_spoke_config_rx_demod_hz(&runtime_config),
        (unsigned long)runtime_config.rmt_resolution_hz,
        (unsigned long)runtime_config.rx_glitch_filter_us,
        (unsigned long)runtime_config.blockage_min_us,
        (unsigned long)runtime_config.blockage_max_us,
        (unsigned long)runtime_config.link_loss_us);

    ir_spoke_pipeline_init(&pipeline);
    ir_spoke_debug_event(IR_SPOKE_DEBUG_STARTUP,
                         "pulse detector and spoke estimator initialized");

    const int ble_result = ir_spoke_ble_csc_start();
    if (ble_result != 0) {
        ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                             "BLE CSC start failed rc=%d", ble_result);
    }
    ESP_ERROR_CHECK(ble_result == 0 ? ESP_OK : ESP_FAIL);

    if (IR_SPOKE_CAN_ENABLED_DEFAULT) {
        ir_spoke_can_transport_t transport = {0};
        ir_spoke_debug_event(IR_SPOKE_DEBUG_CAN,
                             "optional MCP2515 CAN telemetry requested");
        const int can_result = ir_spoke_can_mcp2515_start(&transport);
        if (can_result != 0) {
            ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                                 "MCP2515 start failed rc=%d", can_result);
        }
        ESP_ERROR_CHECK(can_result == 0 ? ESP_OK : ESP_FAIL);
        ir_spoke_can_publisher_init(
            &can_publisher, transport,
            IR_SPOKE_CAN_TELEMETRY_BASE_ID, true);
        ir_spoke_rmt_set_can_publisher(&can_publisher);
        ESP_LOGI("ir_spoke", "optional MCP2515 CAN telemetry enabled");
        ir_spoke_debug_event(IR_SPOKE_DEBUG_CAN,
                             "CAN telemetry publisher ready base_id=0x%03x",
                             IR_SPOKE_CAN_TELEMETRY_BASE_ID);
    } else {
        ir_spoke_debug_event(IR_SPOKE_DEBUG_CAN,
                             "optional MCP2515 CAN telemetry disabled");
    }

    const int rmt_result = ir_spoke_rmt_start(&runtime_config, &pipeline);
    if (rmt_result != 0) {
        ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                             "RMT start failed rc=%d", rmt_result);
    }
    ESP_ERROR_CHECK(rmt_result == 0 ? ESP_OK : ESP_FAIL);

    const esp_err_t link_result =
        ir_spoke_link_monitor_start(&runtime_config);
    if (link_result != ESP_OK) {
        ir_spoke_debug_event(
            IR_SPOKE_DEBUG_ERROR,
            "optical carrier link monitor unavailable: %s",
            esp_err_to_name(link_result));
    }

    ir_spoke_debug_event(IR_SPOKE_DEBUG_STARTUP,
                         "startup complete; sensor is running");
}
