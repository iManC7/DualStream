@echo off
setlocal
echo Removing the DualStream auto-start task...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Stop-ScheduledTask -TaskName 'DualStream Local Agent' -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName 'DualStream Local Agent' -Confirm:$false -ErrorAction SilentlyContinue"
echo Auto-start removed. This does not delete your project files.
pause
