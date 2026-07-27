$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    py -3.14 tools\generate_constants.py
    py -3.14 simulation\ir_spoke_sim.py --monte-carlo 10000
    py -3.14 -m unittest discover -s tests -v
    py -3.14 hardware\ir_spoke_link\generate_schematic.py
    & "C:\Program Files\KiCad\10.0\bin\python.exe" hardware\ir_spoke_link\generate_pcb.py
    & "C:\Program Files\KiCad\10.0\bin\python.exe" hardware\remote_emitter\generate_pcb.py
    & "C:\Program Files\KiCad\10.0\bin\python.exe" hardware\footprint_audit.py
    & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc --output hardware\ir_spoke_link\erc.rpt hardware\ir_spoke_link\ir_spoke_link.kicad_sch
    & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc --output hardware\remote_emitter\drc.rpt hardware\remote_emitter\remote_emitter.kicad_pcb
    npm test
    npm run build
} finally {
    Pop-Location
}
