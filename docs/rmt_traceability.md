# ESP32-S3 RMT traceability

- Zotero parent item: `C5MIHHD4`
- Zotero PDF attachment: `BC9PFKHQ`
- Local mirror: `docs/datasheets/ESP32-S3_TRM.pdf`
- Document: ESP32-S3 TRM, version 1.8, chapter 37
- Driver API cross-check: current stable ESP-IDF Programming Guide v6.0.2
- Hardware relationships used: TX modulation, RX demodulation, RX filtering,
  duration-coded receive symbols.
- ESP-IDF API relationships used: `rmt_new_tx_channel`,
  `rmt_new_rx_channel`, `rmt_new_copy_encoder`, `rmt_apply_carrier`,
  `rmt_rx_register_event_callbacks`, `rmt_enable`, `rmt_receive`,
  `rmt_transmit`.
- RX default: `round(0.66 * f_TX)`. This is the configurable rounded form of
  Espressif's Programming Guide tolerance example (38 kHz TX, 25 kHz RX).
- Captured duration conversion:
  `duration_us = round(duration_ticks * 1e6 / rmt_resolution_hz)`.
- The callback time is the end of the receive transaction. Event starts are
  reconstructed backwards from all returned symbol durations, then advanced
  phase by phase.

The TRM establishes that the ESP32-S3 hardware supports this demodulation.
ESP-IDF supplies the supported software abstraction; no RMT registers are
accessed directly.
