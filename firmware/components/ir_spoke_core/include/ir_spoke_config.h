#ifndef IR_SPOKE_CONFIG_H
#define IR_SPOKE_CONFIG_H

#include <stdint.h>

#include "ir_spoke_generated_c.h"

typedef struct {
    uint32_t carrier_hz;
    float carrier_duty;
    float rx_demod_ratio;
    uint32_t blockage_min_us;
    uint32_t blockage_max_us;
    uint32_t link_loss_us;
} ir_spoke_runtime_config_t;

void ir_spoke_config_defaults(ir_spoke_runtime_config_t *config);
int ir_spoke_config_validate(const ir_spoke_runtime_config_t *config);
uint32_t ir_spoke_config_rx_demod_hz(
    const ir_spoke_runtime_config_t *config);

#endif
