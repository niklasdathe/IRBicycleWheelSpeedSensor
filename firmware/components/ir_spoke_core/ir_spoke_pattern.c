#include "ir_spoke_pattern.h"

#include <float.h>
#include <math.h>
#include <string.h>

static float back(const ir_spoke_pattern_t *p, size_t n) {
    return p->history[(p->history_head + IR_SPOKE_HISTORY_SIZE - 1u - n) %
                      IR_SPOKE_HISTORY_SIZE];
}

static void infer_count(ir_spoke_pattern_t *p) {
    float best = FLT_MAX, second = FLT_MAX;
    uint8_t best_count = 0;
    for (uint8_t n = IR_SPOKE_COUNT_MIN; n <= IR_SPOKE_COUNT_MAX; ++n) {
        if (p->history_size < 2u * n) continue;
        float error = 0.0f, mean = 0.0f;
        for (uint8_t i = 0; i < n; ++i) {
            const float a = back(p, i), b = back(p, i + n);
            mean += 0.5f * (a + b);
            error += fabsf(a - b);
        }
        error = error / fmaxf(mean, 1.0f) * (1.0f + 0.001f * n);
        if (error < best) {
            second = best; best = error; best_count = n;
        } else if (error < second) {
            second = error;
        }
    }
    const float separation = isfinite(second)
        ? (second - best) / fmaxf(second, 1.0e-6f) : 0.0f;
    p->estimate.confidence = fminf(fmaxf(separation, 0.0f), 1.0f);
    if (best_count && best < 0.035f && p->estimate.confidence > 0.08f) {
        p->estimate.spoke_count = best_count;
        p->estimate.count_locked = true;
        for (uint8_t i = 0; i < best_count; ++i)
            p->interval_lut[best_count - 1u - i] = back(p, i);
        p->spoke_index = 0;
    }
}

static void update_map(ir_spoke_pattern_t *p, float interval) {
    const uint8_t n = p->estimate.spoke_count;
    float *cell = &p->interval_lut[p->spoke_index];
    const float previous = *cell > 0.0f ? *cell : interval;
    const float gate = fmaxf(80.0f, IR_SPOKE_OUTLIER_SIGMA * 0.08f * previous);
    if (fabsf(interval - previous) <= gate)
        *cell += IR_SPOKE_LEARNING_RATE * (interval - *cell);
    p->spoke_index = (uint8_t)((p->spoke_index + 1u) % n);
    p->estimate.current_spoke = p->spoke_index;
    float revolution = 0.0f;
    for (uint8_t i = 0; i < n; ++i) revolution += p->interval_lut[i];
    p->estimate.revolution_period_us = revolution;
    p->estimate.wheel_hz = revolution > 0.0f ? 1.0e6f / revolution : 0.0f;
}

void ir_spoke_pattern_init(ir_spoke_pattern_t *p) {
    if (p) memset(p, 0, sizeof(*p));
}

bool ir_spoke_pattern_ingest_edge(ir_spoke_pattern_t *p, uint64_t edge_us) {
    if (!p || !edge_us) return false;
    if (!p->last_edge_us) { p->last_edge_us = edge_us; return false; }
    const float interval = (float)(edge_us - p->last_edge_us);
    p->last_edge_us = edge_us;
    if (interval < IR_SPOKE_BLOCK_MIN_US || interval > IR_SPOKE_LINK_LOSS_US)
        return false;
    p->history[p->history_head] = interval;
    p->history_head = (p->history_head + 1u) % IR_SPOKE_HISTORY_SIZE;
    if (p->history_size < IR_SPOKE_HISTORY_SIZE) ++p->history_size;
    ++p->accepted_events;
    if (!p->estimate.count_locked &&
        p->accepted_events >= IR_SPOKE_CONFIDENCE_EVENTS) infer_count(p);
    if (p->estimate.count_locked) update_map(p, interval);
    return true;
}

const ir_spoke_estimate_t *ir_spoke_pattern_estimate(
    const ir_spoke_pattern_t *p) { return p ? &p->estimate : 0; }
const float *ir_spoke_pattern_lut(const ir_spoke_pattern_t *p) {
    return p ? p->interval_lut : 0;
}
