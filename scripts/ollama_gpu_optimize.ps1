<#
.SYNOPSIS
    Configura variáveis de ambiente para otimização GPU do Ollama
    e reinicia o servidor com as configurações máximas.

.DESCRIPTION
    RTX 4050 6GB GDDR6 + i7-13650HX 14C/20T + 40GB RAM
    
    Otimizações:
    - Flash Attention (menos VRAM, mais throughput)
    - KV Cache Q8 (economia de VRAM)
    - 2 requisições paralelas
    - Até 3 modelos carregados simultaneamente
    - Keep-alive de 15min
#>

$ollamaConfig = @{
    OLLAMA_FLASH_ATTENTION    = "1"
    OLLAMA_KV_CACHE_TYPE      = "q8_0"
    OLLAMA_NUM_PARALLEL       = "2"
    OLLAMA_MAX_LOADED_MODELS  = "3"
    OLLAMA_SCHED_SPREAD       = "1"
    OLLAMA_KEEP_ALIVE         = "15m"
    OLLAMA_GPU_OVERHEAD       = "0"
}

Write-Host "Configurando ambiente Ollama para GPU RTX 4050..." -ForegroundColor Cyan

# Aplica as env vars no processo atual
foreach ($key in $ollamaConfig.Keys) {
    [Environment]::SetEnvironmentVariable($key, $ollamaConfig[$key], "Process")
    Write-Host "  $key = $($ollamaConfig[$key])"
}

# Mata processos ollama existentes
Get-Process ollama -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  Parando Ollama (PID $($_.Id))..." -ForegroundColor Yellow
    $_.Kill()
    Start-Sleep -Seconds 1
}

# Inicia Ollama com as configs
Write-Host "  Iniciando Ollama..." -ForegroundColor Green
$ollamaPath = Get-Command ollama.exe | Select-Object -ExpandProperty Source
Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden

Start-Sleep -Seconds 3

# Verifica se subiu
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/ps" -TimeoutSec 2
    Write-Host "✅ Ollama rodando em http://localhost:11434" -ForegroundColor Green
} catch {
    Write-Host "❌ Falha ao iniciar Ollama" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Otimizações aplicadas:" -ForegroundColor Cyan
foreach ($key in $ollamaConfig.Keys) {
    Write-Host "  $key = $($ollamaConfig[$key])"
}

Write-Host ""
Write-Host "Modelos disponíveis:" -ForegroundColor Cyan
ollama list
