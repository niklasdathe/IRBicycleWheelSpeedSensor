# Getting started

## Prerequisites

The checked scripts currently expect:

| Tool | Expected installation |
|---|---|
| Windows PowerShell | Windows host |
| KiCad | `C:\Program Files\KiCad\10.0` |
| Python | `py -3.14` |
| ngspice | on `PATH`, or `%USERPROFILE%\Tools\ngspice\46\bin\ngspice_con.exe` |

Run commands from the project root.

## Open the authoritative KiCad project

```powershell
.\Open-IR-Spoke-Sensor.cmd
```

The launcher verifies that the captured project is internally consistent, then
opens `hardware/ir_spoke_link/ir_spoke_link.kicad_pro`. Do not open a copied
or generated export as the design source.

## Explore and tune the live model

```powershell
py -3.14 simulation\local_server.py
```

Open `http://127.0.0.1:8765/`. Changing a control runs the same Python transient
used by batch tests. Reset reloads `config/system.json`; code export runs the
selected values through the simulation before returning a C header.

The transient always contains a complete spoke blockage and exposes optical,
TIA, band-pass, comparator, RMT and power traces.

## Run complete verification

```powershell
powershell -ExecutionPolicy Bypass -File tests\run_all.ps1
```

The command regenerates linked constants and topology, runs Python and ngspice,
executes the tolerance sweep and unit/API tests, validates the native KiCad
netlist and footprints, exports the schematic PDF, restores the captured PCB,
then runs ERC and DRC.

Success means every command returns zero and the final DRC reports 0 violations
and 0 unconnected pads. The current ERC has 0 errors and three documented
TLV9062 library-sync warnings. Generated evidence appears under `build/`.

## Read the result

| Question | Location |
|---|---|
| Which requirements passed automatically? | `requirements/verification_matrix.md` |
| Which physical tests remain? | `TODO.md` |
| Which defaults produced the result? | `config/system.json` |
| Which waveform assumptions were used? | `simulation/README.md` |
| Which datasheet values support them? | `docs/datasheet_values.json` |
| Is the captured routing unchanged? | `hardware/ir_spoke_link/layout_manifest.json` |

For edits, continue with [Development workflow](development.md). For ordering,
continue with [Manufacturing](manufacturing.md).
