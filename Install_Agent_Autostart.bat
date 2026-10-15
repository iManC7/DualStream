@echo off
setlocal
cd /d "%~dp0"
echo Installing DualStream background agent for your Windows user...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_Agent_Autostart.ps1"
if errorlevel 1 (
  echo.
  echo Installation failed. Try Run_Local_Agent.bat to diagnose Python/FFmpeg issues.
  pause
  exit /b 1
)
echo.
echo Done. Open the Cloudflare website and use it normally.
pause
