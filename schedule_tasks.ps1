# Registers 3 daily posting runs in Windows Task Scheduler.
# Run once from an elevated or normal PowerShell:  .\schedule_tasks.ps1
# Remove later with:                               .\schedule_tasks.ps1 -Remove

param([switch]$Remove)

$times = @("09:00", "13:30", "19:00")
$script = Join-Path $PSScriptRoot "run.ps1"

for ($i = 0; $i -lt $times.Count; $i++) {
    $name = "SocialAutoPost-$($i + 1)"
    if ($Remove) {
        schtasks /Delete /TN $name /F
        continue
    }
    $action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""
    schtasks /Create /F /TN $name /TR $action /SC DAILY /ST $times[$i]
}

if (-not $Remove) {
    Write-Host ""
    Write-Host "Registered daily runs at: $($times -join ', ')"
    Write-Host "Edit `$times in this script and re-run to change the schedule."
    Write-Host "NOTE: the PC must be awake at those times for posts to go out."
}
