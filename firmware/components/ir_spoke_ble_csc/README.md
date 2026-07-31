# BLE Cycling Speed and Cadence sensor

ESP-IDF 5.x/NimBLE wheel-only Sensor implementation of Bluetooth CSC Profile
1.0 and Service 1.0.1. This component follows the repository's ESP-IDF
component boundary: `app_main` starts it once and the RMT adapter forwards only
completed wheel revolutions after the spoke-pattern estimator is locked.

`register_service()` rejects duplicate registration, preserving the profile's
requirement for exactly one primary CSC service instance.

The public C API is:

```c
ESP_ERROR_CHECK(ir_spoke_ble_csc_start());
ir_spoke_ble_csc_on_wheel_revolution(timestamp_us);
```

The component owns NimBLE initialization, its GAP Peripheral lifecycle,
connectable advertising, subscription tracking, and reconnect advertising.
Notifications are rate-limited to the profile's typical one-second interval.

The module provides CSC Measurement, wheel-only CSC Feature, and the mandatory
Set Cumulative Value control-point procedure, including the required 0x80/0x81
application errors and one-procedure-at-a-time indication lifecycle. Counts
saturate at `UINT32_MAX`; event time uses 1/1024 seconds and rolls over every
64 seconds. Calls into the wheel state are serialized across the RMT and NimBLE
host tasks.
