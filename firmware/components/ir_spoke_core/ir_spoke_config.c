#include "ir_spoke_config.h"

void ir_spoke_config_defaults(ir_spoke_runtime_config_t *c) {
    if (!c) return;
    *c = (ir_spoke_runtime_config_t){
        .tx_gpio = IR_SPOKE_TX_GPIO,
        .rx_gpio = IR_SPOKE_RX_GPIO,
        .carrier_hz = IR_SPOKE_DEFAULT_CARRIER_HZ,
        .carrier_duty = IR_SPOKE_CARRIER_DUTY,
        .rmt_resolution_hz = IR_SPOKE_RMT_RESOLUTION_HZ,
        .rmt_mem_block_symbols = IR_SPOKE_RMT_MEM_BLOCK_SYMBOLS,
        .rmt_tx_queue_depth = IR_SPOKE_RMT_TX_QUEUE_DEPTH,
        .rx_demod_ratio = IR_SPOKE_RX_DEMOD_RATIO,
        .rx_demod_duty = IR_SPOKE_RX_DEMOD_DUTY,
        .rx_glitch_filter_us = IR_SPOKE_GLITCH_FILTER_US,
        .blockage_min_us = IR_SPOKE_BLOCK_MIN_US,
        .blockage_max_us = IR_SPOKE_BLOCK_MAX_US,
        .link_loss_us = IR_SPOKE_LINK_LOSS_US,
    };
}

int ir_spoke_config_validate(const ir_spoke_runtime_config_t *c) {
    if (!c) return -1;
    if (c->tx_gpio < 0 || c->tx_gpio > 48 ||
        c->rx_gpio < 0 || c->rx_gpio > 48 ||
        c->tx_gpio == c->rx_gpio) return -2;
    if (c->carrier_hz < IR_SPOKE_MIN_CARRIER_HZ ||
        c->carrier_hz > IR_SPOKE_MAX_CARRIER_HZ) return -3;
    if (c->carrier_duty < 0.2f || c->carrier_duty > 0.8f) return -4;
    if (c->rmt_resolution_hz < 8u * c->carrier_hz ||
        c->rmt_resolution_hz > 80000000u) return -5;
    if (c->rmt_mem_block_symbols < 48u ||
        c->rmt_mem_block_symbols > 512u ||
        c->rmt_tx_queue_depth < 1u ||
        c->rmt_tx_queue_depth > 8u) return -11;
    if (c->rx_demod_ratio < 0.5f || c->rx_demod_ratio >= 1.0f) return -6;
    if (c->rx_demod_duty < 0.2f || c->rx_demod_duty > 0.8f) return -7;
    if (!c->rx_glitch_filter_us ||
        (float)c->rx_glitch_filter_us * (float)c->carrier_hz >= 0.5e6f)
        return -8;
    if (!c->blockage_min_us ||
        c->blockage_min_us >= c->blockage_max_us) return -9;
    if (c->link_loss_us <= c->blockage_max_us) return -10;
    return 0;
}

uint32_t ir_spoke_config_rx_demod_hz(const ir_spoke_runtime_config_t *c) {
    return c ? (uint32_t)((float)c->carrier_hz * c->rx_demod_ratio) : 0u;
}
