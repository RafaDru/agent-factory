$PidFile = "$PSScriptRoot\.agent-factory\afp.pid"
$LogDir = "$PSScriptRoot\.agent-factory\logs"
$exitCode = 0

Write-Host "=== AFP Healthcheck ===" -ForegroundColor Cyan

# 1. RabbitMQ
try {
    $r = docker ps --filter "name=afp-rabbitmq" --format "{{.Status}}" 2>$null
    if ($r -match "healthy|Up") { Write-Host "[OK] RabbitMQ: $r" -ForegroundColor Green }
    else { Write-Host "[FAIL] RabbitMQ nao encontrado" -ForegroundColor Red; $exitCode = 1 }
} catch { Write-Host "[FAIL] RabbitMQ: $($_.Exception.Message)" -ForegroundColor Red; $exitCode = 1 }

# 2. Dashboard (port 8080)
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8080/api/projects" -UseBasicParsing -TimeoutSec 3
    if ($r.StatusCode -eq 200) { Write-Host "[OK] Dashboard (8080): $($r.StatusCode)" -ForegroundColor Green }
    else { Write-Host "[WARN] Dashboard (8080): $($r.StatusCode)" -ForegroundColor Yellow }
} catch { Write-Host "[FAIL] Dashboard (8080): $($_.Exception.Message)" -ForegroundColor Red; $exitCode = 1 }

# 3. MCP (port 8081) — nao usar /sse (bloqueia); verificar porta TCP
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $iar = $tcp.BeginConnect("localhost", 8081, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(2000, $false)
    if ($ok -and $tcp.Connected) {
        Write-Host "[OK] MCP (8081): porta aberta" -ForegroundColor Green
        $tcp.Close()
    } else {
        Write-Host "[FAIL] MCP (8081): porta fechada ou timeout" -ForegroundColor Red
        $exitCode = 1
    }
} catch {
    Write-Host "[FAIL] MCP (8081): $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}

# 4. Processos AFP
$pids = @()
if (Test-Path $PidFile) {
    $pids = Get-Content $PidFile | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ }
}
if ($pids.Count -eq 0) {
    Write-Host "[FAIL] Nenhum PID encontrado em $PidFile" -ForegroundColor Red; $exitCode = 1
} else {
    $alive = 0
    $dead = @()
    foreach ($p in $pids) {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        if ($proc) { $alive++ } else { $dead += $p }
    }
    if ($dead.Count -eq 0) {
        Write-Host "[OK] Processos: $alive/$($pids.Count) vivos" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Processos: $alive/$($pids.Count) vivos. Mortos: $($dead -join ', ')" -ForegroundColor Red
        $exitCode = 1
    }
}

# 5. Logs
$logCount = (Get-ChildItem "$LogDir\*.err" | Where-Object { $_.Length -gt 0 }).Count
if ($logCount -gt 0) {
    Write-Host "[WARN] $logCount processo(s) com erros no stderr" -ForegroundColor Yellow
    Get-ChildItem "$LogDir\*.err" | Where-Object { $_.Length -gt 0 } | Select-Object Name, @{N="Size";E={"{0:N0}B" -f $_.Length}} | Format-Table -AutoSize
}

Write-Host "---"
if ($exitCode -eq 0) { Write-Host "Status: OPERACIONAL" -ForegroundColor Green }
else { Write-Host "Status: COM FALHAS" -ForegroundColor Red }
exit $exitCode
