@echo off
setlocal
set "KICAD_EXE=C:\Program Files\KiCad\10.0\bin\kicad.exe"
set "KICAD_PY=C:\Program Files\KiCad\10.0\bin\python.exe"
set "PROJECT=%~dp0hardware\ir_spoke_link\ir_spoke_link.kicad_pro"
set "PREFLIGHT=%~dp0hardware\ir_spoke_link\verify_project_entry.py"

if not exist "%KICAD_EXE%" (
  echo KiCad executable not found: %KICAD_EXE%
  pause
  exit /b 1
)

if not exist "%PROJECT%" (
  echo Authoritative KiCad project not found: %PROJECT%
  pause
  exit /b 2
)

"%KICAD_PY%" "%PREFLIGHT%"
if errorlevel 1 (
  echo KiCad project preflight failed. Resolve the message above before opening.
  pause
  exit /b 3
)

powershell -ExecutionPolicy Bypass -File "%~dp0tools\setup_interactive_bom.ps1"
if not errorlevel 1 (
  start "IR Spoke Sensor iBOM" /min py -3.14 "%~dp0tools\interactive_bom.py" --watch --serve --open
)

start "" "%KICAD_EXE%" "%PROJECT%"
endlocal
