# Verification matrix

| Test ID | Method | Automated now | Evidence / status |
|---|---|---:|---|
| T-SIM-001 | Python transient simulation counts valid blockage windows | Yes | `tests/test_system.py` |
| T-CALC-001 | 80 km/h geometry calculation against capture limits | Yes | `tests/test_system.py` |
| T-CFG-001 | Manifest check for wavelength/carrier/duty | Yes | `tests/test_system.py` |
| T-CALC-002 | Installed LED resistor/current calculation | Yes | `tests/test_system.py` |
| T-HW-004 | Harness BOM, connector rating and loop-drop check | Yes | `hardware/cable_bom.csv`, `tests/test_system.py` |
| T-HW-001 | Schematic/BOM architecture inspection | Yes | `tests/test_system.py` |
| T-CALC-003 | RC pole calculation from installed values | Yes | `tests/test_system.py` |
| T-SIM-002 | Comparator and RMT-demodulated waveform assertions | Yes | `tests/test_system.py` |
| T-SIM-003 | TIA headroom assertion | Yes | `tests/test_system.py` |
| T-SW-001 | Generated ESP-IDF source inspection | Yes | `tests/test_system.py` |
| T-ANALYSIS-001 | RMT/MCPWM decision record | Yes | `docs/architecture_decision.md` |
| T-GEN-001 | Regenerate header/SPICE and compare working tree | Yes | `tests/run_all.ps1` |
| T-SW-002 | Non-uniform synthetic pattern count inference | Partial | Algorithm implemented; ESP-IDF host compiler not installed |
| T-SW-003 | Uniform-pattern observability guard | Review | Documented invariant in `spoke_learner.h` |
| T-SW-004 | Source-level LUT/adaptation assertions | Yes | `tests/test_system.py` |
| T-PCB-001 | KiCad Python footprint audit | Yes | `hardware/footprint_audit.py` |
| T-PCB-002 | KiCad DRC | Yes | `hardware/remote_emitter/drc.rpt` |
| T-PCB-003 | Fail-closed export script | Yes | `hardware/export_jlc.ps1` |
| T-DOC-001 | Datasheet extraction manifest cross-check | Yes | `docs/datasheet_values.json`, `tests/test_system.py` |
| T-DOC-002 | Technical HTML parses and covers signal chain, algorithm and open gates | Yes | `public/technical.html`, `tests/test_system.py` |
| T-PHYS-001 | Environmental bench/road test | No | Required before production; see `TODO.md` |

The main carrier board is intentionally not marked verified for fabrication:
placement has been checked, but routing remains open. The export script detects
that state and refuses to emit a misleading Gerber package.
