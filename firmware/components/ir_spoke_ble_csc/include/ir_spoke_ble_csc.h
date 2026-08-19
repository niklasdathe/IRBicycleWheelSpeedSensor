#ifndef IR_SPOKE_BLE_CSC_H
#define IR_SPOKE_BLE_CSC_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Initialize NimBLE, register exactly one CSC primary service, and start the
 * Peripheral host. Advertising begins after host synchronization. */
int ir_spoke_ble_csc_start(void);

/* Forward one completed wheel revolution, never an individual spoke event.
 * Measurements are notified at no more than the profile's typical 1 Hz rate. */
void ir_spoke_ble_csc_on_wheel_revolution(uint64_t timestamp_us);

#ifdef __cplusplus
}
#endif

#endif
