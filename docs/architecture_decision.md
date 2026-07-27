# ADR-001: RMT RX instead of MCPWM Capture for the raw comparator carrier

Status: accepted for the current hardware.

The custom analog front end intentionally stops at a Schmitt comparator. Its
output is therefore a clean 38 kHz logic carrier whenever the optical path is
clear and stops while a spoke blocks the beam.

ESP32-S3 RMT is the better fit for that signal because the peripheral supports
RX carrier demodulation, glitch filtering, symbol-duration capture and RX DMA.
The firmware can receive missing-carrier windows without servicing 38,000 edge
interrupts per second. Espressif also recommends configuring the RX demodulator
below the theoretical transmit frequency; the generated value is 25 kHz for a
38 kHz transmitter.

MCPWM Capture has a high-resolution APB-clock timestamp and is excellent when
the input is already a baseband edge. On ESP32-S3 its requested resolution is
ignored because the capture timer uses the APB source. Using it here would
either expose every carrier edge to the capture path or require another analog
envelope detector. That adds parts without improving spoke-time accuracy.

Revisit this decision only if a future board adds an external envelope detector,
or if RMT resources are consumed by another subsystem.
