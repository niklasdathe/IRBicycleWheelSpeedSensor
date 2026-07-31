$ErrorActionPreference = "Stop"
$ToolRoot = Join-Path $env:USERPROFILE "Tools\InteractiveHtmlBom\2.11.2"
$ExpectedCommit = "de7fad7ead9b73cea7eb17afa02c6ce9ce17a6ab"
$Generator = Join-Path $ToolRoot "InteractiveHtmlBom\generate_interactive_bom.py"

if (-not (Test-Path -LiteralPath $Generator)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $ToolRoot) |
        Out-Null
    git clone --depth 1 --branch v2.11.2 `
        https://github.com/openscopeproject/InteractiveHtmlBom.git $ToolRoot
    if ($LASTEXITCODE -ne 0) {
        throw "InteractiveHtmlBom clone failed"
    }
}

$ActualCommit = git -C $ToolRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualCommit.Trim() -ne $ExpectedCommit) {
    throw "InteractiveHtmlBom exists but is not pinned to v2.11.2/$ExpectedCommit"
}

Write-Host "PASS: InteractiveHtmlBom v2.11.2 is installed at $ToolRoot"
