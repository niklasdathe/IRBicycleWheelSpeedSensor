$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}
Push-Location $Root
try {
    py -3.14 tools\generate_constants.py
    Assert-NativeSuccess "generate_constants"
    py -3.14 hardware\ir_spoke_link\generate_schematic.py
    Assert-NativeSuccess "generate_schematic"
    py -3.14 tools\generate_connectivity.py
    Assert-NativeSuccess "generate_connectivity"
    py -3.14 simulation\ir_spoke_sim.py --monte-carlo 10000
    Assert-NativeSuccess "Python simulation"
    py -3.14 simulation\validate_ngspice.py
    Assert-NativeSuccess "ngspice cross-check"
    py -3.14 tools\build_konnect_jlc_db.py
    Assert-NativeSuccess "Konnect database build"
    py -3.14 tools\interactive_bom.py --check
    Assert-NativeSuccess "interactive BOM sync"
    py -3.14 tools\readme_pcb_render.py --check
    Assert-NativeSuccess "README PCB render sync"
    py -3.14 tools\versioning.py
    Assert-NativeSuccess "hardware/software version links"
    py -3.14 tools\verify_hardware_release.py
    Assert-NativeSuccess "ordered hardware release package"
    py -3.14 tools\audit_project.py
    Assert-NativeSuccess "project link audit"
    py -3.14 -m unittest discover -s tests -v
    Assert-NativeSuccess "Python unit tests"
    py -3.14 tools\validate_kicad_netlist.py
    Assert-NativeSuccess "KiCad netlist validation"
    & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch export pdf --output hardware\ir_spoke_link\ir_spoke_link_schematic.pdf hardware\ir_spoke_link\ir_spoke_link.kicad_sch
    Assert-NativeSuccess "schematic PDF export"
    & "C:\Program Files\KiCad\10.0\bin\python.exe" hardware\ir_spoke_link\generate_pcb.py
    Assert-NativeSuccess "main PCB generation"
    & "C:\Program Files\KiCad\10.0\bin\python.exe" hardware\footprint_audit.py
    Assert-NativeSuccess "footprint audit"
    & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc --output hardware\ir_spoke_link\erc.rpt hardware\ir_spoke_link\ir_spoke_link.kicad_sch
    Assert-NativeSuccess "schematic ERC"
    & "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" pcb drc --refill-zones --output hardware\ir_spoke_link\drc.rpt hardware\ir_spoke_link\ir_spoke_link.kicad_pcb
    Assert-NativeSuccess "main PCB DRC"
} finally {
    Pop-Location
}
