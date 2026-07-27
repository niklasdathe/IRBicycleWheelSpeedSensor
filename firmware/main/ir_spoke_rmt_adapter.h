#ifndef IR_SPOKE_RMT_ADAPTER_H
#define IR_SPOKE_RMT_ADAPTER_H

#include "ir_spoke_config.h"
#include "ir_spoke_pipeline.h"

/* ESP-IDF boundary. Core state and configuration remain caller-owned. */
int ir_spoke_rmt_start(const ir_spoke_runtime_config_t *config,
                       ir_spoke_pipeline_t *pipeline);

#endif
