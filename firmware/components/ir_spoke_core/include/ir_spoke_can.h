#ifndef IR_SPOKE_CAN_H
#define IR_SPOKE_CAN_H

#include <stdbool.h>
#include <stdint.h>

#include "ir_spoke_pattern.h"

typedef struct {
    uint32_t identifier;
    uint8_t length;
    uint8_t data[8];
} ir_spoke_can_frame_t;

typedef int (*ir_spoke_can_send_fn)(
    void *context, const ir_spoke_can_frame_t *frame);

typedef struct {
    ir_spoke_can_send_fn send;
    void *context;
} ir_spoke_can_transport_t;

typedef struct {
    ir_spoke_can_transport_t transport;
    uint16_t base_identifier;
    uint16_t sequence;
    bool enabled;
} ir_spoke_can_publisher_t;

void ir_spoke_can_publisher_init(
    ir_spoke_can_publisher_t *publisher,
    ir_spoke_can_transport_t transport,
    uint16_t base_identifier,
    bool enabled);

int ir_spoke_can_publish_estimate(
    ir_spoke_can_publisher_t *publisher,
    const ir_spoke_estimate_t *estimate,
    uint32_t blockage_duration_us);

#endif
