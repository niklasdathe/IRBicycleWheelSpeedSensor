#include "esp_check.h"
#include "ir_spoke_config.h"
#include "ir_spoke_pipeline.h"
#include "ir_spoke_rmt_adapter.h"

static ir_spoke_runtime_config_t runtime_config;
static ir_spoke_pipeline_t pipeline;

void app_main(void) {
    ir_spoke_config_defaults(&runtime_config);
    /* Application code may change carrier_hz before start, within the
       generated analog-compatible bounds. */
    ir_spoke_pipeline_init(&pipeline);
    ESP_ERROR_CHECK(ir_spoke_rmt_start(&runtime_config, &pipeline));
}
