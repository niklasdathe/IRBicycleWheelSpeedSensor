#include "ir_spoke_detector.h"

void ir_spoke_detector_init(ir_spoke_detector_t *d, uint32_t minimum_us,
                            uint32_t maximum_us) {
    if (!d) return;
    *d = (ir_spoke_detector_t){.minimum_us = minimum_us,
                              .maximum_us = maximum_us};
}

ir_spoke_pulse_result_t ir_spoke_detector_ingest(ir_spoke_detector_t *d,
                                                  uint32_t duration_us) {
    if (duration_us < d->minimum_us) {
        ++d->rejected_short;
        return IR_SPOKE_PULSE_REJECT_SHORT;
    }
    if (duration_us > d->maximum_us) {
        ++d->rejected_long;
        return IR_SPOKE_PULSE_REJECT_LONG;
    }
    ++d->accepted;
    return IR_SPOKE_PULSE_ACCEPTED;
}
