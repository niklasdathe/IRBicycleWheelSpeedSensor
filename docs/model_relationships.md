# Executable relationships

| Source | Generated or checked consumers |
|---|---|
| `config/system.json` | firmware headers, SPICE parameters, Python defaults, local UI reset |
| `hardware/connectivity.json` | schematic/PCB audits, native KiCad netlist gate, SPICE topology and topology hash |
| `hardware/component_catalog.json` | schematic/PCB fields, BOM, footprint audit and JLC/Konnect metadata |
| `docs/datasheet_values.json` | model limits, requirements checks and technical documentation |
| `hardware/ir_spoke_link/*.layout.kicad_*` | byte-identical schematic/PCB/preferences regeneration |
| `hardware/ir_spoke_link/layout_manifest.json` | layout, route, rotations, DRC and net-endpoint integrity gates |
| `simulation/ir_spoke_sim.py` | local API, generated experiment header and batch evidence |
| `simulation/ir_spoke_link.cir` | ngspice cross-check against the Python transient |
| `requirements/requirements.yaml` | verification-ID coverage in `requirements/verification_matrix.md` |
| `hardware/ir_spoke_link/bom_jlcpcb.csv` | R4 export, live JLC snapshot and Konnect project database |

The combined PCB is the only emitter-board source. The breakaway transmitter is
part of the same captured board, BOM, CPL, connectivity contract and DRC gate.
Generated simulation results live under `build/`; the source tree contains no
second cached simulation dataset.

Run `tools/audit_project.py` for path/reference integrity and
`tests/run_all.ps1` for the complete executable chain.
