$ErrorActionPreference = 'Stop'
$taskName = 'DualStream Local Agent'
$scriptPath = Join-Path $PSScriptRoot 'DualStream_Local_Agent.py'
if (-not (Test-Path $scriptPath)) { throw "Missing agent script: $scriptPath" }

# Resolve the active Python interpreter through the Python launcher.
$pythonExe = (& py -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1).Trim()
if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    throw 'Python 3 was not found. Install Python 3 and enable the Python launcher (py), then retry.'
}
$pythonw = Join-Path (Split-Path $pythonExe -Parent) 'pythonw.exe'
if (-not (Test-Path $pythonw)) {
    throw "pythonw.exe was not found next to $pythonExe. Reinstall Python with the standard Windows installer and retry."
}

$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + $scriptPath + '"') -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'DualStream local FFmpeg controller; starts quietly at sign-in, FFmpeg starts only when requested from the website.' -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 2
try {
    $null = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/status' -TimeoutSec 3
    Write-Host 'DualStream agent installed and responding.' -ForegroundColor Green
    Write-Host 'It will now start quietly when you sign in to Windows.'
    Write-Host 'FFmpeg will still start only when you press Start on the website.'
} catch {
    Write-Warning 'The task was installed, but the agent did not respond yet. Check agent.log or run Run_Local_Agent.bat to diagnose.'
}
