# IR Spoke Link

Compact burst-modulated 38 kHz / 940 nm infrared link for a Seeed Studio XIAO ESP32S3 carrier,
designed to remain detectable while bicycle spokes periodically block the
beam.

The project is intentionally linked:

- `config/system.json` is the single source for wheel, optical and electrical
  assumptions.
- `simulation/ir_spoke_sim.py` produces `public/simulation.json`.
- The web visualizer renders those generated traces and can explore parameter
  variations interactively.
- `simulation/ir_spoke_link.cir` mirrors the circuit-level behavioral model.
- `hardware/ir_spoke_link` contains the KiCad project, design rules and JLCPCB
  BOM.
- `firmware/esp32s3_rmt_example.cpp` documents the matching ESP32-S3 RMT setup.

This is a prototype engineering design, not a certified safety system.
