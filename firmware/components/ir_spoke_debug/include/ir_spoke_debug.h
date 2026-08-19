#ifndef IR_SPOKE_DEBUG_H
#define IR_SPOKE_DEBUG_H

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    IR_SPOKE_DEBUG_STARTUP = 0,
    IR_SPOKE_DEBUG_RMT,
    IR_SPOKE_DEBUG_RMT_CAPTURE,
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

esp_err_t ir_spoke_debug_init(void);
void ir_spoke_debug_event(ir_spoke_debug_event_t event,
                          const char *format, ...);

#ifdef __cplusplus
}
#endif

#endif
