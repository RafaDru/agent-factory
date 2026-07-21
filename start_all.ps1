param(
    [switch]$NoRabbitMQ,
    [switch]$NoRuntimes,
    [switch]$NoDashboard
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

# 1. RabbitMQ
if (-not $NoRabbitMQ) {
    Write-Host "=== Iniciando RabbitMQ ===" -ForegroundColor Cyan
    & "$Root\docker-start.ps1"
}

# 2. MCP Server + Dashboard
Write-Host "=== Iniciando servidores ===" -ForegroundColor Cyan
$afp = Start-Process -WindowStyle Hidden -FilePath python -ArgumentList "-m", "src.mcp.server", "--sse", "--port", "8081" -PassThru
Start-Sleep -Seconds 2
$dash = Start-Process -WindowStyle Hidden -FilePath python -ArgumentList "-m", "src.dashboard.server" -PassThru
Start-Sleep -Seconds 2

Write-Host "AFP MCP Server: PID $($afp.Id)" -ForegroundColor Green
Write-Host "Dashboard:      PID $($dash.Id)" -ForegroundColor Green
Write-Host "RabbitMQ UI:    http://localhost:15672 (afp/afp123)" -ForegroundColor Green
Write-Host "Dashboard:      http://localhost:8080" -ForegroundColor Green

# 3. Agent Runtimes (opcional, via Event Bus)
if (-not $NoRuntimes) {
    Start-Sleep -Seconds 3
    Write-Host "=== Iniciando agent runtimes (RabbitMQ) ===" -ForegroundColor Cyan
    
    $agents = @(
        @{id="dev"; class="src.agents.worker.DeclarativeWorker"}
        @{id="qa"; class="src.agents.worker.DeclarativeWorker"}
        @{id="designer"; class="src.agents.worker.DeclarativeWorker"}
        @{id="arquiteto"; class="src.agents.worker.DeclarativeWorker"}
        @{id="negocios"; class="src.agents.worker.DeclarativeWorker"}
    )
    
    $runtimePids = @()
    foreach ($a in $agents) {
        $proc = Start-Process -WindowStyle Hidden -FilePath python -ArgumentList @(
            "-m", "src.agents.runtime", $a.class, $a.id, "AFP-Team"
        ) -PassThru
        $runtimePids += $proc.Id
        Write-Host "  Runtime $($a.id): PID $($proc.Id)" -ForegroundColor DarkYellow
        Start-Sleep -Milliseconds 500
    }
    
    Write-Host "Total runtimes: $($runtimePids.Count)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Para parar tudo: Stop-Process -Id <PID> ou use o script stop_all.ps1" -ForegroundColor Yellow
