#include "esp_check.h"
#include "esp_log.h"
#include "ir_spoke_can.h"
#include "ir_spoke_can_mcp2515_adapter.h"
#include "ir_spoke_ble_csc.h"
#include "ir_spoke_config.h"
#include "ir_spoke_pipeline.h"
#include "ir_spoke_rmt_adapter.h"

static ir_spoke_runtime_config_t runtime_config;
static ir_spoke_pipeline_t pipeline;
static ir_spoke_can_publisher_t can_publisher;

void app_main(void) {
    ir_spoke_config_defaults(&runtime_config);
    /* Application code may change carrier_hz before start, within the
       generated analog-compatible bounds. */
    ir_spoke_pipeline_init(&pipeline);
    ESP_ERROR_CHECK(ir_spoke_ble_csc_start());
    if (IR_SPOKE_CAN_ENABLED_DEFAULT) {
        ir_spoke_can_transport_t transport = {0};
        const int can_result = ir_spoke_can_mcp2515_start(&transport);
        ESP_ERROR_CHECK(can_result == 0 ? ESP_OK : ESP_FAIL);
        ir_spoke_can_publisher_init(
            &can_publisher, transport,
            IR_SPOKE_CAN_TELEMETRY_BASE_ID, true);
        ir_spoke_rmt_set_can_publisher(&can_publisher);
        ESP_LOGI("ir_spoke", "optional MCP2515 CAN telemetry enabled");
    }
    ESP_ERROR_CHECK(ir_spoke_rmt_start(&runtime_config, &pipeline));
}
