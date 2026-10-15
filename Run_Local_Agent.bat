@echo off
setlocal
cd /d "%~dp0"
rem Set this to your exact Cloudflare Pages/Worker website origin after deployment.
set "DUALSTREAM_ALLOWED_ORIGIN=https://ds.aymanalboqami.workers.dev"
py "%~dp0DualStream_Local_Agent.py"
if errorlevel 1 pause
endlocal
