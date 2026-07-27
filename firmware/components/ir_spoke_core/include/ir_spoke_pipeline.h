#ifndef IR_SPOKE_PIPELINE_H
#define IR_SPOKE_PIPELINE_H

#include "ir_spoke_detector.h"
#include "ir_spoke_pattern.h"

typedef struct {
    ir_spoke_detector_t detector;
    ir_spoke_pattern_t pattern;
} ir_spoke_pipeline_t;

void ir_spoke_pipeline_init(ir_spoke_pipeline_t *pipeline);
ir_spoke_pulse_result_t ir_spoke_pipeline_ingest(
    ir_spoke_pipeline_t *pipeline, uint64_t edge_timestamp_us,
    uint32_t blockage_duration_us);

#endif
