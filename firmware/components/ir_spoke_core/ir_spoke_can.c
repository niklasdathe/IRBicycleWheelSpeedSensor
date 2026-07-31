#include "ir_spoke_can.h"

#include <math.h>
#include <string.h>

static void put_u16_le(uint8_t *target, uint16_t value) {
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
}

void ir_spoke_can_publisher_init(
    ir_spoke_can_publisher_t *p,
    ir_spoke_can_transport_t transport,
    uint16_t base_identifier,
    bool enabled) {
    if (!p) return;
    memset(p, 0, sizeof(*p));
    p->transport = transport;
    p->base_identifier = base_identifier;
    p->enabled = enabled;
}

int ir_spoke_can_publish_estimate(
    ir_spoke_can_publisher_t *p,
    const ir_spoke_estimate_t *estimate,
    uint32_t blockage_duration_us) {
    if (!p || !estimate) return -1;
    if (!p->enabled) return 0;
    if (!p->transport.send) return -2;

    const float wheel_millihz_f = estimate->wheel_hz * 1000.0f;
    const uint16_t wheel_millihz = (uint16_t)fminf(
        fmaxf(wheel_millihz_f, 0.0f), 65535.0f);
    const uint16_t duration = (uint16_t)(
        blockage_duration_us > 65535u ? 65535u : blockage_duration_us);
    const uint16_t confidence_permille = (uint16_t)fminf(
        fmaxf(estimate->confidence * 1000.0f, 0.0f), 1000.0f);

    ir_spoke_can_frame_t frame = {
        .identifier = p->base_identifier,
        .length = 8,
        .data = {
            estimate->spoke_count,
            estimate->current_spoke,
            0, 0, 0, 0, 0, 0,
        },
    };
    put_u16_le(&frame.data[2], wheel_millihz);
    put_u16_le(&frame.data[4], duration);
    put_u16_le(&frame.data[6], confidence_permille);
    const int result = p->transport.send(p->transport.context, &frame);
    if (result == 0) ++p->sequence;
    return result;
}
