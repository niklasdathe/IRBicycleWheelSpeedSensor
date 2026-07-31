# Optional XIAO CAN interface

Hardware: official Seeed XIAO CAN Bus Expansion Board, SKU 105100001,
MCP2515 controller with 16 MHz crystal and SN65HVD230 3.3 V transceiver.

| XIAO pin | ESP32-S3 GPIO | CAN function | IR conflict |
|---|---:|---|---|
| D6 | 43 | MCP2515 INT | none |
| D7 | 44 | MCP2515 CS | none |
| D8 | 7 | SPI SCK | none |
| D9 | 8 | SPI MISO | none |
| D10 | 9 | SPI MOSI | none |
| D0 | 1 | IR RMT TX | CAN unused |
| D1 | 2 | IR RMT RX | CAN unused |

Default CAN bitrate: 500 kbit/s. SPI: 10 MHz, mode 0. Compile-time
`_Static_assert` checks prevent future IR/CAN pin overlap.

Interfaces:

- `ir_spoke_can`: portable frame encoding and caller-supplied send callback.
- `ir_spoke_can_mcp2515_adapter`: ESP-IDF `spi_master` and MCP2515 register
  protocol for the official board.
- `ir_spoke_rmt_adapter`: publishes one estimate frame after each accepted
  blockage when the CAN publisher is enabled.

Standard ID `0x180` payload:

| Byte | Field | Encoding |
|---:|---|---|
| 0 | inferred spoke count | unsigned |
| 1 | current spoke index | unsigned |
| 2–3 | wheel frequency | little-endian mHz |
| 4–5 | blockage duration | little-endian µs |
| 6–7 | confidence | little-endian per mille |

`config/system.json` is authoritative. `tools/generate_constants.py` writes
the pin map, oscillator, bitrate, SPI clock, enable default and CAN ID into
firmware and SPICE constants. The localhost simulator exposes CAN enable and
bus-duty inputs and plots `can_current_ma`.

Official sources and Zotero keys are recorded in
`docs/zotero_links.json`.
