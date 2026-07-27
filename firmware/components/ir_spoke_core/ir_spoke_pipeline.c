#include "ir_spoke_pipeline.h"

void ir_spoke_pipeline_init(ir_spoke_pipeline_t *p) {
    if (!p) return;
    ir_spoke_detector_init(&p->detector, IR_SPOKE_BLOCK_MIN_US,
                           IR_SPOKE_BLOCK_MAX_US);
    ir_spoke_pattern_init(&p->pattern);
}

ir_spoke_pulse_result_t ir_spoke_pipeline_ingest(
    ir_spoke_pipeline_t *p, uint64_t edge_us, uint32_t duration_us) {
    if (!p) return IR_SPOKE_PULSE_REJECT_LONG;
    const ir_spoke_pulse_result_t result =
        ir_spoke_detector_ingest(&p->detector, duration_us);
    if (result == IR_SPOKE_PULSE_ACCEPTED)
        (void)ir_spoke_pattern_ingest_edge(&p->pattern, edge_us);
    return result;
}
