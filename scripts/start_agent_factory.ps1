<#
.SYNOPSIS
    Agent Factory — Windows Startup
    Inicia Ollama com otimizações GPU + Dashboard.

.DESCRIPTION
    Passos:
    1. Configura variáveis de ambiente para GPU (Flash Attention, KV Cache, paralelismo)
    2. Inicia Ollama (se não estiver rodando)
    3. Lista modelos disponíveis
    4. Sobe o Dashboard em http://localhost:8080

.PARAMETER Port
    Porta do dashboard (default: 8080)

.PARAMETER Demo
    Executa agentes de demonstração no startup

.PARAMETER NoOllama
    Não gerencia o Ollama (útil se já estiver rodando manualmente)

.EXAMPLE
    .\scripts\start_agent_factory.ps1
    .\scripts\start_agent_factory.ps1 -Port 9090 -Demo
#>

param(
    [int]$Port = 8080,
    [switch]$Demo,
    [switch]$NoOllama
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

Write-Host @"

    +----------------------------------------------+
    |        Agent Factory -- v2.0.0-beta           |
    |             Windows Startup                   |
    +----------------------------------------------+

"@ -ForegroundColor Cyan

# ─── Step 1: Ollama ────────────────────────────────────────────────────
if (-not $NoOllama) {
    Write-Host "`n[1/3] Configurando Ollama..." -ForegroundColor Yellow

    # GPU optimization env vars
    $env:OLLAMA_FLASH_ATTENTION   = "1"
    $env:OLLAMA_KV_CACHE_TYPE     = "q8_0"
    $env:OLLAMA_NUM_PARALLEL      = "2"
    $env:OLLAMA_MAX_LOADED_MODELS = "3"
    $env:OLLAMA_SCHED_SPREAD      = "1"
    $env:OLLAMA_KEEP_ALIVE        = "15m"

    Write-Host "  OLLAMA_FLASH_ATTENTION   = $env:OLLAMA_FLASH_ATTENTION" -ForegroundColor Gray
    Write-Host "  OLLAMA_KV_CACHE_TYPE     = $env:OLLAMA_KV_CACHE_TYPE" -ForegroundColor Gray
    Write-Host "  OLLAMA_NUM_PARALLEL      = $env:OLLAMA_NUM_PARALLEL" -ForegroundColor Gray
    Write-Host "  OLLAMA_MAX_LOADED_MODELS = $env:OLLAMA_MAX_LOADED_MODELS" -ForegroundColor Gray
    Write-Host "  OLLAMA_KEEP_ALIVE        = $env:OLLAMA_KEEP_ALIVE" -ForegroundColor Gray

    # Check if Ollama is already running
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
        Write-Host "  ✅ Ollama já está rodando" -ForegroundColor Green
    } catch {
        Write-Host "  🚀 Iniciando Ollama..." -ForegroundColor Yellow
        $ollamaPath = (Get-Command ollama.exe -ErrorAction SilentlyContinue).Source
        if (-not $ollamaPath) {
            Write-Host "  ❌ Ollama não encontrado. Instale: https://ollama.com" -ForegroundColor Red
            exit 1
        }
        $proc = Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 3
        Write-Host "  ✅ Ollama rodando (PID $($proc.Id))" -ForegroundColor Green
    }

    # List models
    Write-Host "`n[2/3] Modelos disponíveis:" -ForegroundColor Yellow
    try {
        $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
        if ($tags.models.Count -gt 0) {
            $tags.models | Sort-Object size -Descending | ForEach-Object {
                $size = [math]::Round($_.size / 1GB, 1)
                Write-Host "  • $($_.name) ($size GB)" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ⚠️  Nenhum modelo instalado" -ForegroundColor Yellow
            Write-Host "     Execute: ollama pull gemma3:4b" -ForegroundColor Gray
            Write-Host "     Execute: ollama pull qwen2.5-coder:7b" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠️  Não foi possível listar modelos" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[1/3] ⏭️  Ollama: gerenciamento desabilitado (--NoOllama)" -ForegroundColor Gray
    Write-Host "[2/3] ⏭️  Modelos: pulado" -ForegroundColor Gray
}
# ─── Step 2: Dashboard ─────────────────────────────────────────────────
Write-Host "`n[3/3] Iniciando Dashboard..." -ForegroundColor Yellow

$pythonArgs = @(
    "`"$RootDir\start_agent_factory.py`"",
    "--port", $Port,
    "--no-ollama"
)
if ($Demo) { $pythonArgs += "--demo" }

Write-Host "  http://localhost:$Port/?project=agent-factory-dev" -ForegroundColor Cyan
Write-Host "  Pressione Ctrl+C para encerrar" -ForegroundColor Gray
Write-Host ""

# Execute (replaces the current process)
& python $pythonArgs
