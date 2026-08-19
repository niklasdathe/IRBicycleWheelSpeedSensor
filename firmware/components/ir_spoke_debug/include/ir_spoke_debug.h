#ifndef IR_SPOKE_DEBUG_H
#define IR_SPOKE_DEBUG_H

#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    IR_SPOKE_DEBUG_STARTUP = 0,
    IR_SPOKE_DEBUG_RMT,
    IR_SPOKE_DEBUG_RMT_CAPTURE,
    IR_SPOKE_DEBUG_LINK,
    IR_SPOKE_DEBUG_PULSE_ACCEPTED,
    IR_SPOKE_DEBUG_PULSE_REJECTED,
    IR_SPOKE_DEBUG_ESTIMATOR,
    IR_SPOKE_DEBUG_REVOLUTION,
    IR_SPOKE_DEBUG_BLE,
    IR_SPOKE_DEBUG_BLE_NOTIFY,
    IR_SPOKE_DEBUG_CAN,
    IR_SPOKE_DEBUG_CAN_TX,
    IR_SPOKE_DEBUG_ERROR,
} ir_spoke_debug_event_t;

typedef enum {
    IR_SPOKE_LINK_UNKNOWN = 0,
    IR_SPOKE_LINK_DOWN,
    IR_SPOKE_LINK_UP,
} ir_spoke_link_state_t;

esp_err_t ir_spoke_debug_init(void);
void ir_spoke_debug_event(ir_spoke_debug_event_t event,
                          const char *format, ...);

/* Legacy RMT-envelope observation. Retained for source compatibility; the
 * hardware PCNT carrier monitor is authoritative for optical-link status. */
void ir_spoke_debug_link_state(ir_spoke_link_state_t state,
                               uint32_t clear_us,
                               uint32_t max_blocked_us);

void ir_spoke_debug_carrier_link_state(ir_spoke_link_state_t state,
                                       uint32_t measured_carrier_hz,
                                       uint32_t expected_carrier_hz,
                                       uint32_t rising_edges,
                                       uint32_t sample_ms);

#ifdef __cplusplus
}
#endif

#endif
