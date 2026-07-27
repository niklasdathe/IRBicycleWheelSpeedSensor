#ifndef IR_SPOKE_PATTERN_H
#define IR_SPOKE_PATTERN_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "ir_spoke_generated_c.h"

#define IR_SPOKE_HISTORY_SIZE (2u * IR_SPOKE_COUNT_MAX + 8u)

typedef struct {
    uint8_t spoke_count;
    uint8_t current_spoke;
    bool count_locked;
    float confidence;
    float revolution_period_us;
    float wheel_hz;
} ir_spoke_estimate_t;

typedef struct {
    float history[IR_SPOKE_HISTORY_SIZE];
    float interval_lut[IR_SPOKE_COUNT_MAX];
    size_t history_head;
    size_t history_size;
    uint64_t last_edge_us;
    uint32_t accepted_events;
    uint8_t spoke_index;
    ir_spoke_estimate_t estimate;
} ir_spoke_pattern_t;

void ir_spoke_pattern_init(ir_spoke_pattern_t *pattern);
bool ir_spoke_pattern_ingest_edge(ir_spoke_pattern_t *pattern,
                                  uint64_t edge_timestamp_us);
const ir_spoke_estimate_t *ir_spoke_pattern_estimate(
    const ir_spoke_pattern_t *pattern);
const float *ir_spoke_pattern_lut(const ir_spoke_pattern_t *pattern);

#endif
