#ifndef IR_SPOKE_GEOMETRY_H
#define IR_SPOKE_GEOMETRY_H

#include <stdint.h>

typedef struct {
    float wheel_hz;
    float wheel_rpm;
    float event_hz;
    float blockage_us;
} ir_spoke_geometry_result_t;

int ir_spoke_geometry_calculate(float speed_kmh, float wheel_diameter_m,
                                float beam_radius_m, float spoke_width_mm,
                                uint8_t spoke_count,
                                ir_spoke_geometry_result_t *out);

#endif
