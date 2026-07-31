param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^V\d+\.\d+$')]
    [string]$Revision
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$KiCad = "C:\Program Files\KiCad\10.0\bin"
$KiPython = Join-Path $KiCad "python.exe"
$Cli = Join-Path $KiCad "kicad-cli.exe"
$Board = Join-Path $PSScriptRoot "ir_spoke_link\ir_spoke_link.kicad_pcb"
$Product = "IR_Spoke_Sensor_${Revision}_2L"
$ProjectManifest = Get-Content -Raw -LiteralPath (
    Join-Path $Root "project_manifest.json"
) | ConvertFrom-Json
$CadRevision = $ProjectManifest.revision
$ExpectedHardwareVersion = $ProjectManifest.hardware_version -replace '-dev$', ''
if ($Revision -ne $ExpectedHardwareVersion) {
    throw "Requested $Revision does not match project hardware version $($ProjectManifest.hardware_version)."
}
$ExportRoot = Join-Path $PSScriptRoot "jlc_export"
$Out = Join-Path $ExportRoot $Product
$FabricationLayers = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

& $KiPython (Join-Path $PSScriptRoot "ir_spoke_link\generate_pcb.py")
& $KiPython (Join-Path $PSScriptRoot "footprint_audit.py")
py -3.14 (Join-Path $Root "tools\interactive_bom.py") --check
if ($LASTEXITCODE -ne 0) {
    throw "Interactive BOM is stale; regenerate it before manufacturing export."
}

$ResolvedRoot = [IO.Path]::GetFullPath($ExportRoot).TrimEnd(
    [IO.Path]::DirectorySeparatorChar
) + [IO.Path]::DirectorySeparatorChar
$ResolvedOut = [IO.Path]::GetFullPath($Out).TrimEnd(
    [IO.Path]::DirectorySeparatorChar
) + [IO.Path]::DirectorySeparatorChar
if (-not $ResolvedOut.StartsWith(
    $ResolvedRoot, [StringComparison]::OrdinalIgnoreCase
)) {
    throw "Refusing to clear export path outside $ResolvedRoot"
}
if (Test-Path -LiteralPath $Out) {
    Remove-Item -LiteralPath $Out -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$AssemblyReference = Join-Path $Out "assembly_reference"
New-Item -ItemType Directory -Force -Path $AssemblyReference | Out-Null

$Drc = Join-Path $Out "${Product}_DRC.rpt"
& $Cli pcb drc --refill-zones --output $Drc $Board
$Report = Get-Content -Raw -LiteralPath $Drc
if ($Report -notmatch "\*\* Found 0 DRC violations \*\*" -or
    $Report -notmatch "\*\* Found 0 unconnected pads \*\*") {
    throw "Combined $Revision board is not fabrication-ready. See $Drc. Export stopped before Gerbers."
}

$Temporary = Join-Path $Out "_versioned_source"
New-Item -ItemType Directory -Path $Temporary | Out-Null
$VersionedBoard = Join-Path $Temporary "${Product}.kicad_pcb"
Copy-Item -LiteralPath $Board -Destination $VersionedBoard
& $Cli pcb export gerbers --layers $FabricationLayers --check-zones `
    --output $Out $VersionedBoard
& $Cli pcb export drill --output $Out $VersionedBoard
& $Cli pcb export gerbers --layers "F.Courtyard,B.Courtyard" `
    --output $AssemblyReference $VersionedBoard

$Bom = Join-Path $Out "${Product}_BOM.csv"
$Cpl = Join-Path $Out "${Product}_CPL.csv"
& $KiPython (Join-Path $PSScriptRoot "generate_jlc_assembly.py") `
    $Board --bom $Bom --cpl $Cpl

$OrderSpec = @{
    project = "IR Spoke Sensor"
    hardware_version = $Revision
    cad_revision = $CadRevision
    filename_prefix = $Product
    layers = 2
    material = "FR-4"
    thickness_mm = 1.6
    copper_weight_oz = 1
    panel_size_mm = @(21, 37.9)
    carrier_section_mm = @(17.8, 21.4)
    emitter_section_mm = @(21, 15)
    separation = "one routed conductive mouse-bite breakaway tab"
    breakaway_tab_mm = @(7.5, 1.5)
    mouse_bite = @{
        count = 5
        drill_mm = 0.5
        pitch_mm = 1.5
    }
    temporary_links = @("3V3", "LED_K")
    assembly_side = "top"
    note = "Request engineering review of routed tab and mouse-bites. Temporary copper links are intentionally severed at snap-off."
    courtyard_reference = "Separate non-fabrication Gerbers only; do not upload as production layers."
}
$OrderSpec | ConvertTo-Json -Depth 4 |
    Set-Content -Encoding utf8 (Join-Path $Out "${Product}_ORDER.json")
$Order = Join-Path $Out "${Product}_ORDER.json"

$ManufacturingFiles = Get-ChildItem -LiteralPath $Out -File |
    Where-Object {
        $_.Extension -in @(
            ".gtl", ".gbl", ".gtp", ".gbp", ".gto", ".gbo",
            ".gts", ".gbs", ".gm1", ".gbr", ".drl", ".gbrjob"
        )
    }
if ($ManufacturingFiles.Count -ne 11) {
    throw "Expected 11 Gerber/drill/job files; found $($ManufacturingFiles.Count)."
}
$GerberZip = Join-Path $Out "${Product}_GERBER.zip"
Compress-Archive -Force -LiteralPath $ManufacturingFiles.FullName `
    -DestinationPath $GerberZip
$AssemblyZip = Join-Path $Out "${Product}_PCBA.zip"
Compress-Archive -Force -LiteralPath @(
    $Bom, $Cpl, $Order
) -DestinationPath $AssemblyZip
$CourtyardFiles = Get-ChildItem -LiteralPath $AssemblyReference -File |
    Where-Object { $_.Extension -eq ".gbr" }
if ($CourtyardFiles.Count -ne 2) {
    throw "Expected two courtyard-reference Gerbers; found $($CourtyardFiles.Count)."
}
$CourtyardZip = Join-Path $Out "${Product}_COURTYARD_REFERENCE.zip"
Compress-Archive -Force -LiteralPath $CourtyardFiles.FullName `
    -DestinationPath $CourtyardZip
$CableBom = Join-Path $PSScriptRoot "cable_bom.csv"
$InteractiveBom = Join-Path $Root "docs\interactive_bom.html"
$ChecksumTargets = @(
    $GerberZip,
    $AssemblyZip,
    $Bom,
    $Cpl,
    $Order,
    $Drc,
    $CourtyardZip,
    $CableBom,
    $InteractiveBom
)
$Checksums = Join-Path $Out "${Product}_SHA256SUMS.txt"
$ChecksumTargets | ForEach-Object {
    $Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $_
    "{0}  {1}" -f $Hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $_)
} | Set-Content -Encoding ascii -LiteralPath $Checksums
$ReleaseZip = Join-Path $Out "${Product}_ORDER_PACKAGE.zip"
Compress-Archive -Force -LiteralPath @(
    $GerberZip,
    $AssemblyZip,
    $Bom,
    $Cpl,
    $Order,
    $Drc,
    $CourtyardZip,
    $CableBom,
    $InteractiveBom,
    $Checksums
) -DestinationPath $ReleaseZip
Remove-Item -LiteralPath $Temporary -Recurse -Force
Write-Host "PASS: $Product DRC-gated JLC order package completed."
