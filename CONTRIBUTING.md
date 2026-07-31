# Contributing

This project treats CAD, simulation, firmware and requirements as one linked
design. A change is complete only when its authoritative input, generated
consumers, documentation and verification agree.

## Choose the authoritative input

| Change | Edit first | Then run |
|---|---|---|
| Carrier, wheel, analog or power value | `config/system.json` | `tests/run_all.ps1` |
| Pin, net or cable topology | `hardware/connectivity.json` | `tools/generate_connectivity.py`, then full tests |
| Part or procurement data | `hardware/component_catalog.json` | footprint audit and JLC export |
| Portable algorithm | `firmware/components/ir_spoke_core/` | unit tests |
| ESP-IDF peripheral integration | `firmware/main/` | target build plus unit tests |
| Requirement | `requirements/requirements.yaml` | update the verification matrix and test |
| Schematic or PCB placement/routing | live KiCad files | capture only after all editors are closed |

Do not hand-edit generated headers, SPICE parameter includes, connectivity
includes, BOM/CPL files or JLC export archives.

## CAD preservation rule

The PCB contains user-authored routing. Automation may inspect it, restore the
captured state and export it; automation must never route or alter tracks.

For an intentional KiCad edit:

1. Open the project with `Open-IR-Spoke-Sensor.cmd`.
2. Make and save the manual change.
3. Close every KiCad editor.
4. Run `py -3.14 hardware\ir_spoke_link\capture_layout.py`.
5. Run the complete verification command below.
6. Inspect the schematic PDF, PCB, DRC report and changed hashes before
   accepting the capture.

Capture fails on ERC, DRC, open pads, net drift or routing drift. A component
move that requires rerouting must leave those tracks for the board author.

## Required verification

```powershell
powershell -ExecutionPolicy Bypass -File tests\run_all.ps1
```

Expected terminal condition: every generator, simulation, link audit, unit
test, netlist check, ERC, DRC and footprint audit reports success.

For a manufacturing change, also run:

```powershell
powershell -ExecutionPolicy Bypass -File hardware\export_jlc.ps1 -Revision R4
```

Review the JLC assembly preview manually. Automated rotation checks do not
replace visual polarity confirmation.

## Documentation rule

- Put status and task entry points in `README.md`.
- Put procedures in the task guide that owns them.
- Put rationale and extracted evidence in the focused reference documents.
- Link to the authoritative value instead of copying it.
- Mark simulated, inspected and physically measured claims distinctly.
- Keep every relative Markdown link valid; `tools/audit_project.py` enforces
  this.
