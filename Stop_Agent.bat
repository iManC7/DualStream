@echo off
setlocal
echo Stopping DualStream local agent (and any active FFmpeg process it owns)...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$taskName='DualStream Local Agent'; Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; $p=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'DualStream_Local_Agent\.py' }; foreach ($x in $p) { Stop-Process -Id $x.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host 'Stop request completed.' -ForegroundColor Green"
echo You can start it again with Start_Agent.bat.
pause
endlocal
