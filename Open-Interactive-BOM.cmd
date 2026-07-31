@echo off
setlocal
set "ROOT=%~dp0"
powershell -ExecutionPolicy Bypass -File "%ROOT%tools\setup_interactive_bom.ps1"
if errorlevel 1 (
  echo InteractiveHtmlBom setup failed.
  pause
  exit /b 1
)
py -3.14 "%ROOT%tools\interactive_bom.py" --watch --serve --open
endlocal
