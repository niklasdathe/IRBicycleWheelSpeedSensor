# Changelog

Hardware and software are versioned independently. Hardware entries describe
manufactured PCB states; software entries describe firmware behavior.

## Hardware

### V0.2 — Unreleased

Changes relative to the ordered V0.1 baseline:

- Development line opened; no electrical, mechanical, placement or routing
  change has been made yet.
- Hardware changes must be recorded here before a future V0.2 release.

### V0.1 — 2026-07-31

Ordered baseline, corresponding to KiCad CAD revision R4 and Git tag `V0.1`.

- Two-layer 17.8 x 21.4 mm XIAO receiver carrier.
- Breakaway 940 nm emitter board with two M2.5 mounting holes.
- Conductive mouse-bite tab for pre-snap functional testing.
- Discrete TLV9062/TLV7011 receiver and RMT-based ESP32-S3 interface.
- Right-angle JST-GH remote-emitter connection and optional XIAO CAN board.
- JLCPCB Gerber, BOM, CPL, order metadata and checksum package released.

## Software

### SW-V0.1.0 — Unreleased

- Portable adaptive spoke-learning core and ESP-IDF RMT integration are under
  development; no software release is implied by hardware V0.1.
