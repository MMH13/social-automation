# Entry point used by Task Scheduler. Logs to state\runs.log.
Set-Location -LiteralPath $PSScriptRoot

# Ensure ffmpeg (winget install) is on PATH even in a minimal scheduler environment
$ffmpegBin = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ffmpegBin) { $env:PATH = "$($ffmpegBin.DirectoryName);$env:PATH" }

python -m src.main
