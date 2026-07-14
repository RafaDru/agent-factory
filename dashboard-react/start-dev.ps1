param(
  [string]$LogFile = "vite-dev.log"
)

$ProjectDir = $PSScriptRoot
$LogPath = Join-Path $ProjectDir $LogFile

# Use cmd.exe internal redirection to merge stdout+stderr into same file
$process = Start-Process -FilePath "cmd.exe" -WindowStyle Hidden -PassThru -ArgumentList @("/c", "npm run dev -- --host > ""$LogPath"" 2>&1") -WorkingDirectory $ProjectDir

Write-Host "Vite dev server started in background (PID: $($process.Id))"
Write-Host "Log file: $LogPath"
Write-Host ""
Write-Host "To view log:"
Write-Host "  Get-Content -Path ""$LogPath"" -Tail 20"
Write-Host "  Get-Content -Path ""$LogPath"" -Wait"
Write-Host ""
Write-Host "To stop server:"
Write-Host "  Stop-Process -Id $($process.Id)"
