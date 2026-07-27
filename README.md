# IR Spoke Link

Compact continuous-carrier 38 kHz / 940 nm infrared spoke sensor for a Seeed
Studio XIAO ESP32-S3 carrier. A remote emitter shines across the spoke plane
into a discrete photodiode, transimpedance amplifier, active band-pass and
Schmitt comparator. No integrated 38 kHz receiver or hidden AGC is used.

The project is intentionally linked:

- `config/system.json` is the single source for wheel, optical and electrical
  assumptions.
- `simulation/ir_spoke_sim.py` produces `public/simulation.json`.
- The web visualizer renders those generated traces and can explore parameter
  variations interactively.
- `simulation/ir_spoke_link.cir` mirrors the component-valued circuit model.
- `hardware/ir_spoke_link` contains the main KiCad carrier project.
- `hardware/remote_emitter` contains the routed remote LED board.
- `hardware/export_jlc.ps1` performs footprint audit and DRC-gated JLC export.
- `firmware/esp32s3_rmt_example.cpp` uses ESP32-S3 RMT carrier generation and
  hardware carrier removal; generated constants come from the same config.

The main PCB is placed but intentionally not exported until its remaining open
connections are routed. The remote emitter is routed and DRC-clean.

This is a prototype engineering design, not a certified safety system.

Technical documentation: `public/technical.html` (served as `/technical.html`).
