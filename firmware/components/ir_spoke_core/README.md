# ir_spoke_core

Portable C99; no heap, RTOS or ESP-IDF dependency.

- `ir_spoke_geometry`: wheel/spoke timing calculation.
- `ir_spoke_config`: validated runtime carrier/demodulation configuration.
- `ir_spoke_detector`: blockage-width acceptance and counters.
- `ir_spoke_pattern`: count inference, confidence and adaptive interval LUT.
- `ir_spoke_pipeline`: explicit detector-to-pattern composition boundary.
- `ir_spoke_can`: transport-independent fixed-frame telemetry publisher.

Inputs are integer microsecond timestamps/durations. State is caller-owned.
Each module can be host-tested without GPIO or RMT hardware.

The ESP-IDF layer owns RMT and the official XIAO MCP2515 SPI protocol. CAN is
disabled by default and can be enabled through the generated system baseline.
