@echo off
setlocal
set "TASK=DualStream Local Agent"
echo Starting DualStream local agent...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$t=Get-ScheduledTask -TaskName '%TASK%' -ErrorAction SilentlyContinue; if (-not $t) { Write-Host 'Task not installed. Run Install_Agent_Autostart.bat first.' -ForegroundColor Red; exit 2 }; if ((Get-ScheduledTaskInfo -TaskName '%TASK%').State -eq 'Running') { Write-Host 'Agent is already running.' -ForegroundColor Green; exit 0 }; Start-ScheduledTask -TaskName '%TASK%'; Start-Sleep -Seconds 2; try { $null=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/status' -TimeoutSec 3; Write-Host 'Agent is running.' -ForegroundColor Green } catch { Write-Host 'Start was requested, but the agent is not responding yet. Check agent.log.' -ForegroundColor Yellow; exit 1 }"
if errorlevel 1 pause
endlocal
