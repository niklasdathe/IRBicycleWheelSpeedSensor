#ifndef IR_SPOKE_LINK_MONITOR_H
#define IR_SPOKE_LINK_MONITOR_H

#include "esp_err.h"
#include "ir_spoke_config.h"

#ifdef __cplusplus
extern "C" {
#endif

esp_err_t ir_spoke_link_monitor_start(
    const ir_spoke_runtime_config_t *config);

#ifdef __cplusplus
}
#endif

#endif
