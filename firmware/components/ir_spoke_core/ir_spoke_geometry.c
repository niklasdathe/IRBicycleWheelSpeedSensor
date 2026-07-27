#include "ir_spoke_geometry.h"

#include <math.h>

int ir_spoke_geometry_calculate(float speed_kmh, float wheel_diameter_m,
                                float beam_radius_m, float spoke_width_mm,
                                uint8_t spoke_count,
                                ir_spoke_geometry_result_t *out) {
    if (!out || speed_kmh <= 0.0f || wheel_diameter_m <= 0.0f ||
        beam_radius_m <= 0.0f || spoke_width_mm <= 0.0f || spoke_count == 0) {
        return -1;
    }
    const float pi = 3.14159265358979323846f;
    out->wheel_hz = (speed_kmh / 3.6f) / (pi * wheel_diameter_m);
    out->wheel_rpm = 60.0f * out->wheel_hz;
    out->event_hz = (float)spoke_count * out->wheel_hz;
    out->blockage_us = 1.0e6f * (spoke_width_mm * 1.0e-3f) /
                        (2.0f * pi * out->wheel_hz * beam_radius_m);
    return 0;
}
