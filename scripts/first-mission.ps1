param(
    [string]$ProjectId = "demo-onboarding",
    [switch]$SkipDocker,
    [switch]$SkipInstall,
    [switch]$SkipMission
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== AFP First Mission ===" -ForegroundColor Cyan
Write-Host "Repo: $Root"
Write-Host "Projeto: $ProjectId"
Write-Host ""

# 1. .env
$envFile = Join-Path $Root ".env"
$envExample = Join-Path $Root ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Host "[WARN] .env criado a partir de .env.example — preencha GROQ_API_KEY (ou outro provider)" -ForegroundColor Yellow
}

# 2. Dependencias
if (-not $SkipInstall) {
    Write-Host "[1/5] Instalando dependencias..." -ForegroundColor Gray
    python -m pip install -q -e ".[llm,dev]"
    if ($LASTEXITCODE -ne 0) { throw "pip install falhou" }
}

# 3. RabbitMQ
if (-not $SkipDocker) {
    Write-Host "[2/5] RabbitMQ (docker compose)..." -ForegroundColor Gray
    docker compose up -d rabbitmq 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Docker/RabbitMQ indisponivel — continuando em Modo Lite (in-process)" -ForegroundColor Yellow
    } else {
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "[2/5] RabbitMQ ignorado (-SkipDocker)" -ForegroundColor Gray
}

# 4. Stack AFP
Write-Host "[3/5] Subindo stack AFP..." -ForegroundColor Gray
& (Join-Path $Root "start_afp.ps1") -Restart -ProjectId $ProjectId
if ($LASTEXITCODE -ne 0) { throw "start_afp.ps1 falhou" }
Start-Sleep -Seconds 4

# 5. Healthcheck
Write-Host "[4/5] Healthcheck..." -ForegroundColor Gray
& (Join-Path $Root "start_afp.ps1") -HealthCheck
$hc = $LASTEXITCODE
if ($hc -ne 0) {
    Write-Host "[WARN] Healthcheck retornou $hc — tentando repair..." -ForegroundColor Yellow
    & (Join-Path $Root "start_afp.ps1") -Repair
    Start-Sleep -Seconds 3
    & (Join-Path $Root "start_afp.ps1") -HealthCheck
    if ($LASTEXITCODE -ne 0) { throw "Healthcheck falhou apos repair" }
}

# 6. Primeira missao
if (-not $SkipMission) {
    Write-Host "[5/5] Executando primeira missao (smoke)..." -ForegroundColor Gray
    python (Join-Path $Root "run_smoke_e012.py")
    $missionExit = $LASTEXITCODE
    if ($missionExit -ne 0) {
        Write-Host ""
        Write-Host "FIRST_MISSION_FAIL — verifique .env (API key) e logs em .agent-factory/logs/" -ForegroundColor Red
        exit $missionExit
    }
}

Write-Host ""
Write-Host "FIRST_MISSION_OK" -ForegroundColor Green
Write-Host "  Dashboard: http://localhost:8080"
Write-Host "  MCP SSE:   http://127.0.0.1:8081/sse"
Write-Host "  Proximo:   peca a IA run_objective(project_id='$ProjectId', ...)"
Write-Host "  Guia:      docs/AI_ONBOARDING.md"
exit 0
