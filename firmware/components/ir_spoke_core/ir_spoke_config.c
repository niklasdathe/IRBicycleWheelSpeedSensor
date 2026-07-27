#include "ir_spoke_config.h"

void ir_spoke_config_defaults(ir_spoke_runtime_config_t *c) {
    if (!c) return;
    *c = (ir_spoke_runtime_config_t){
        .carrier_hz = IR_SPOKE_DEFAULT_CARRIER_HZ,
        .carrier_duty = IR_SPOKE_CARRIER_DUTY,
        .rx_demod_ratio = IR_SPOKE_RX_DEMOD_RATIO,
        .blockage_min_us = IR_SPOKE_BLOCK_MIN_US,
        .blockage_max_us = IR_SPOKE_BLOCK_MAX_US,
        .link_loss_us = IR_SPOKE_LINK_LOSS_US,
    };
}

int ir_spoke_config_validate(const ir_spoke_runtime_config_t *c) {
    if (!c) return -1;
    if (c->carrier_hz < IR_SPOKE_MIN_CARRIER_HZ ||
        c->carrier_hz > IR_SPOKE_MAX_CARRIER_HZ) return -2;
    if (c->carrier_duty < 0.2f || c->carrier_duty > 0.8f) return -3;
    if (c->rx_demod_ratio < 0.5f || c->rx_demod_ratio >= 1.0f) return -4;
    if (!c->blockage_min_us ||
        c->blockage_min_us >= c->blockage_max_us) return -5;
    if (c->link_loss_us <= c->blockage_max_us) return -6;
    return 0;
}

uint32_t ir_spoke_config_rx_demod_hz(const ir_spoke_runtime_config_t *c) {
    return c ? (uint32_t)((float)c->carrier_hz * c->rx_demod_ratio) : 0u;
}
