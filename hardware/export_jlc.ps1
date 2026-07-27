$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$KiCad = "C:\Program Files\KiCad\10.0\bin"
$KiPython = Join-Path $KiCad "python.exe"
$Cli = Join-Path $KiCad "kicad-cli.exe"

& $KiPython (Join-Path $PSScriptRoot "ir_spoke_link\generate_pcb.py")
& $KiPython (Join-Path $PSScriptRoot "remote_emitter\generate_pcb.py")
& $KiPython (Join-Path $PSScriptRoot "footprint_audit.py")

$Boards = @(
    @{Name="remote_emitter"; Path=(Join-Path $PSScriptRoot "remote_emitter\remote_emitter.kicad_pcb"); Bom=(Join-Path $PSScriptRoot "remote_emitter\bom_jlcpcb.csv")},
    @{Name="main"; Path=(Join-Path $PSScriptRoot "ir_spoke_link\ir_spoke_link.kicad_pcb"); Bom=(Join-Path $PSScriptRoot "ir_spoke_link\bom_jlcpcb.csv")}
)
foreach ($Board in $Boards) {
    $Out = Join-Path $PSScriptRoot "jlc_export\$($Board.Name)"
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    $Drc = Join-Path $Out "drc.rpt"
    & $Cli pcb drc --refill-zones --output $Drc $Board.Path
    $Report = Get-Content -Raw -LiteralPath $Drc
    if ($Report -notmatch "\*\* Found 0 DRC violations \*\*" -or
        $Report -notmatch "\*\* Found 0 unconnected pads \*\*") {
        throw "$($Board.Name) is not fabrication-ready. See $Drc. Export stopped before Gerbers."
    }
    & $Cli pcb export gerbers --output $Out $Board.Path
    & $Cli pcb export drill --output $Out $Board.Path
    & $Cli pcb export pos --format csv --units mm --output (Join-Path $Out "positions.csv") $Board.Path
    Copy-Item -Force -LiteralPath $Board.Bom -Destination (Join-Path $Out "bom_jlcpcb.csv")
    Compress-Archive -Force -Path (Join-Path $Out "*.gbr"),(Join-Path $Out "*.drl") -DestinationPath (Join-Path $Out "gerbers.zip")
}
Write-Host "PASS: DRC-gated JLC export completed."
