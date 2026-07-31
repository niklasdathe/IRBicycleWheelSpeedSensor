# Verification matrix

| Test ID | Method | Automated now | Evidence / status |
|---|---|---:|---|
| T-SIM-001 | Python transient simulation counts valid blockage windows | Yes | `tests/test_system.py` |
| T-CALC-001 | 80 km/h geometry calculation against capture limits | Yes | `tests/test_system.py` |
| T-CFG-001 | Runtime carrier boundary/default and wavelength/duty checks | Yes | `tests/test_system.py` |
| T-CALC-002 | Installed LED resistor/current calculation | Yes | `tests/test_system.py` |
| T-HW-004 | Harness BOM, connector rating and loop-drop check | Yes | `hardware/cable_bom.csv`, `tests/test_system.py` |
| T-HW-001 | Schematic/BOM architecture inspection | Yes | `tests/test_system.py` |
| T-CALC-003 | RC response calculation at 25, 38 and 50 kHz | Yes | `tests/test_system.py` |
| T-SIM-002 | Comparator and RMT-demodulated waveform assertions | Yes | `tests/test_system.py` |
| T-SIM-003 | TIA headroom assertion | Yes | `tests/test_system.py` |
| T-SIM-004 | 10,000-case tolerance/environment sweep | Yes | `simulation/ir_spoke_sim.py`, `tests/run_all.ps1` |
| T-SW-001 | Generated ESP-IDF source inspection | Yes | `tests/test_system.py` |
| T-ANALYSIS-001 | RMT/MCPWM decision record | Yes | `docs/architecture_decision.md` |
| T-GEN-001 | Regenerate header/SPICE and compare working tree | Yes | `tests/run_all.ps1` |
| T-SW-002 | Portable C99 module/interface and no-heap audit | Yes | `tests/test_system.py` |
| T-SW-003 | Pattern-inference source/host-model review | Partial | C module implemented; target compiler not installed |
| T-SW-004 | Source-level LUT/adaptation assertions | Yes | `tests/test_system.py` |
| T-SW-005 | Official ESP-IDF RMT API and runtime-field relationship inspection | Yes | `tests/test_system.py` |
| T-API-001 | Local API defaults, simulation and generated C header | Yes | `tests/test_local_server.py` |
| T-SIM-005 | Short/long transient centred-blockage and extended-trace assertions | Yes | `tests/test_system.py` |
| T-PWR-001 | Datasheet-based average/peak power and transient-trace assertions | Yes | `simulation/ir_spoke_sim.py`, `tests/test_system.py` |
| T-CAN-001 | Official XIAO CAN pin-map, SPI limit and optional worst-case power assertions | Yes | `docs/datasheet_values.json`, `tests/test_system.py` |
| T-SW-006 | Portable CAN publisher and isolated ESP-IDF MCP2515/SPI adapter audit | Yes | `firmware/components/ir_spoke_core/ir_spoke_can.c`, `firmware/main/ir_spoke_can_mcp2515_adapter.c` |
| T-NET-001 | KiCad-native XML netlist, PCB pads and SPICE SHA against canonical manifest | Yes | `tools/validate_kicad_netlist.py`, `hardware/footprint_audit.py`, `simulation/connectivity_guard.py` |
| T-DBG-001 | Required testpoint net/pad and no-PD-summing-node-probe audit | Yes | `hardware/connectivity.json`, `hardware/footprint_audit.py`, `tests/test_system.py` |
| T-KONNECT-001 | SQLite integrity/schema/row-scope test | Yes | `tests/test_system.py`, `hardware/konnect_database_manifest.json` |
| T-PCB-001 | KiCad Python footprint audit | Yes | `hardware/footprint_audit.py` |
| T-PCB-002 | KiCad DRC | Yes | Combined receiver/emitter panel: 0 findings / 0 open pads |
| T-PCB-003 | Fail-closed export script | Yes | `hardware/export_jlc.ps1` |
| T-PCB-004 | Main-board routed-state gate | Yes | `hardware/ir_spoke_link/drc.rpt`; 0 findings, 0 unconnected pads, fabrication-ready true |
| T-PCB-005 | Captured layout, trace/via/angle/zone/courtyard audit | Yes | `hardware/ir_spoke_link/layout_manifest.json`, `hardware/footprint_audit.py` |
| T-PCB-006 | Exact receiver/transmitter dimensions, rounded-corner outline, single conductive tab, net ties, mouse-bites, emitter parts and M2.5-hole audit | Yes | `hardware/footprint_audit.py` |
| T-PCB-007 | Right-angle JST-GH MPN/LCSC/footprint/pin-map, courtyard and 3D-model audit with protected routing signature | Yes | `hardware/component_catalog.json`, `hardware/connectivity.json`, `hardware/footprint_audit.py`, `hardware/ir_spoke_link/layout_integrity.py` |
| T-PCB-008 | KiCad editor-layer preference plus separate front/back courtyard Gerber export | Yes | `hardware/ir_spoke_link/ir_spoke_link.kicad_prl`, `hardware/export_jlc.ps1` |
| T-DOC-001 | Datasheet extraction manifest cross-check | Yes | `docs/datasheet_values.json`, `tests/test_system.py` |
| T-DOC-002 | Technical HTML parses and covers signal chain, algorithm and open gates | Yes | `local_simulator/technical.html`, `tests/test_system.py` |
| T-DOC-003 | Daylight-filter datasheet field and layered ambient-rejection rationale | Yes | `docs/datasheet_values.json`, `docs/debug_and_threshold.md`, `tests/test_system.py` |
| T-DOC-004 | Task-guide structure, visible maturity/release gates, authoritative-source map, local Markdown links and documentation-index coverage | Yes | `README.md`, `docs/README.md`, `tools/audit_project.py`, `tests/test_system.py` |
| T-DOC-005 | KiCad-sourced InteractiveHtmlBom output, pinned generator, source/output hashes, procurement fields and live-watch entry point | Yes | `docs/interactive_bom.html`, `docs/interactive_bom.json`, `tools/interactive_bom.py`, `tests/test_system.py` |
| T-PHYS-001 | Environmental bench/road test | No | Required before production; see `TODO.md` |

The combined receiver/emitter panel passes KiCad DRC with the captured physical
footprint orientations. U1/U2/J3/J4 corrections exist only in the JLC
CPL generator; D1 uses the required 180-degree LCSC/KiCad convention correction
and D2 uses zero degrees. JLC assembly-preview approval,
bench correlation and environmental validation remain required before release.
