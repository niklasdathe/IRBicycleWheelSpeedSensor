# Connectivity contract

`hardware/connectivity.json` is the canonical pin-to-net definition for both
boards and the two resistive harness conductors.

Consumers and gates:

- `hardware/ir_spoke_link/capture_layout.py` through the native netlist gate;
- the hash-verified main-board schematic/PCB layout templates;
- `tools/generate_connectivity.py` for SPICE;
- `hardware/footprint_audit.py`.

`tools/validate_kicad_netlist.py` independently asks KiCad to export its native
XML netlist and compares all 70 connected schematic pins with the manifest.
`simulation/connectivity_guard.py` hashes the manifest and refuses every batch
or local API simulation if `simulation/generated_connectivity.inc` is stale.

This catches symbol transforms, swapped active-device pins, connector mistakes,
PCB pad-net drift and stale SPICE topology. It does not prove track routing:
KiCad DRC remains the routing gate. After restoring the physical footprint
orientations and moving the correction into CPL-only rotation offsets, both
the combined receiver/emitter panel has zero findings and zero open
connections. Its layout capture
additionally freezes the 197 user segments, 12 vias and raw route-expression
SHA-256.
