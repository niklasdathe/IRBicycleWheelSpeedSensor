# Active engineering TODOs

- [x] Replace the AGC IR receiver module with a fully controlled photodiode/TIA/band-pass/comparator front end.
- [x] Compare MCPWM Capture with RMT RX carrier removal and document the selection.
- [x] Generate ESP-IDF compile-time constants and SPICE parameters from `config/system.json`.
- [x] Add online spoke-count inference and an adaptive per-spoke interval LUT without manual calibration.
- [x] Split the emitter onto a remote PCB and define the 600 mm JST-GH/AWG28 harness.
- [x] Reorganize the schematic into readable functional blocks.
- [x] Add the remote-emitter connector, cable and assembly items to the BOM and schematic.
- [x] Retry the project move and verify the new authoritative copy; old workspace remains locked by the desktop session.
- [x] Route and DRC-clean the remote emitter PCB.
- [x] Audit all footprint pad sets, assigned nets and LCSC metadata.
- [x] Add terse technical HTML documentation for modulation, analog chain, RMT demodulation and adaptive spoke learning.
- [ ] Route the main carrier PCB; current placed board has no geometric DRC violations but 41 open connections.
- [ ] Run physical sunlight/alignment tests and write measured photocurrent/noise values back to `config/system.json`.
- [ ] Re-run the simulation and compile firmware with the measured parameter set.
- [ ] Upload both boards to JLCPCB's BOM/CPL preview and confirm rotations against the rendered assembly view.
- [ ] Remove `C:\Users\nikla\OneDrive\Dokumente\Bicycle OBU` after Codex releases its workspace handle; the authoritative project is now under `Projekte\IR Spoke Sensor`.
