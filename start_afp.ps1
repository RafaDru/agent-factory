param([switch]$Stop)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = "$Root\.agent-factory\logs"
$PidFile = "$Root\.agent-factory\afp.pid"
New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction SilentlyContinue | Out-Null

if ($Stop) {
    if (Test-Path $PidFile) {
        $pids = Get-Content $PidFile
        $pids | ForEach-Object { try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } catch {} }
        Remove-Item $PidFile
    }
    Write-Output "AFP parado"
    return
}

# Kill existing AFP processes
$existing = Get-Process -Name python,pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Id -gt 0 }
if ($existing) {
    $existing | ForEach-Object {
        try { $cmd = $_.CommandLine -join ' ' } catch { return }
        if ($cmd -match 'src\.(dashboard\.server|mcp\.server|agents\.runtime)') {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep 2
}

function Start-AfpProcess {
    param([string]$Name, [string]$Arguments)
    $logFile = "$LogDir\$Name.log"
    $errFile = "$LogDir\$Name.err"
    "=== Started at $(Get-Date) ===" | Out-File $logFile -Encoding UTF8
    "=== Started at $(Get-Date) ===" | Out-File $errFile -Encoding UTF8
    $proc = Start-Process -FilePath python.exe -ArgumentList $Arguments -WorkingDirectory $Root `
        -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errFile -PassThru
    Start-Sleep -Milliseconds 200
    if ($proc.HasExited) {
        $exitCode = $proc.ExitCode
        $err = Get-Content $errFile -Raw -ErrorAction SilentlyContinue
        Write-Host "[FAIL] $Name exit=$exitCode" -ForegroundColor Red
        if ($err) { Write-Host "  STDERR: $($err.Substring(0,[Math]::Min(500,$err.Length)))" -ForegroundColor Red }
    } else {
        Write-Host "[OK] $Name (PID $($proc.Id))" -ForegroundColor Green
    }
    return $proc.Id
}

$pids = @()
Write-Output "Iniciando AFP..."

$pids += Start-AfpProcess -Name "dashboard" -Arguments "$Root\_run_dashboard.py"
$pids += Start-AfpProcess -Name "mcp" -Arguments "-m src.mcp.server --sse --port 8081"

Start-Sleep 1
$pids += Start-AfpProcess -Name "coordinator" -Arguments "-m src.agents.runtime src.agents.coordinator.AgentFactoryCoordinator coordenador AFP-Team"

Start-Sleep 1
foreach ($a in @("dev","qa","designer","arquiteto","negocios")) {
    $pids += Start-AfpProcess -Name "runtime-$a" -Arguments "-m src.agents.runtime src.agents.worker.DeclarativeWorker $a AFP-Team"
    Start-Sleep -Milliseconds 500
}

$pids | Out-File $PidFile -Encoding ASCII
Write-Output "---"
Write-Output "AFP rodando. Logs em: $LogDir"
Write-Output "Healthcheck: Get-Process -Name python | Where-Object { (`$_.CommandLine -join ' ') -match 'src\.(agents|mcp|dashboard)' }"
