#ifndef IR_SPOKE_DETECTOR_H
#define IR_SPOKE_DETECTOR_H

#include <stdint.h>

typedef enum {
    IR_SPOKE_PULSE_REJECT_SHORT = -1,
    IR_SPOKE_PULSE_REJECT_LONG = -2,
    IR_SPOKE_PULSE_ACCEPTED = 1
} ir_spoke_pulse_result_t;

typedef struct {
    uint32_t minimum_us;
    uint32_t maximum_us;
    uint32_t accepted;
    uint32_t rejected_short;
    uint32_t rejected_long;
} ir_spoke_detector_t;

void ir_spoke_detector_init(ir_spoke_detector_t *detector,
                            uint32_t minimum_us, uint32_t maximum_us);
ir_spoke_pulse_result_t ir_spoke_detector_ingest(ir_spoke_detector_t *detector,
                                                  uint32_t duration_us);

#endif
