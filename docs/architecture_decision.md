# ADR-001: RMT RX instead of MCPWM Capture for the raw comparator carrier

Status: accepted for the current hardware.

The custom analog front end intentionally stops at a Schmitt comparator. Its
output is therefore a clean logic carrier at the selected 25–50 kHz transmit
frequency whenever the optical path is clear and stops while a spoke blocks
the beam.

ESP32-S3 RMT is the better fit for that signal because the peripheral supports
RX carrier demodulation, glitch filtering, symbol-duration capture and RX DMA.
The firmware can receive missing-carrier windows without servicing every
carrier edge. The RX demodulator frequency is derived at runtime as 0.66 times
the selected TX frequency, not stored as a second fixed frequency.

MCPWM Capture has a high-resolution APB-clock timestamp and is excellent when
the input is already a baseband edge. On ESP32-S3 its requested resolution is
ignored because the capture timer uses the APB source. Using it here would
either expose every carrier edge to the capture path or require another analog
envelope detector. That adds parts without improving spoke-time accuracy.

Revisit this decision only if a future board adds an external envelope detector,
or if RMT resources are consumed by another subsystem.

The 25–50 kHz range is an engineering constraint of the installed analog
filter, not a protocol requirement. Values outside it are rejected by
`ir_spoke_config_validate()`.
