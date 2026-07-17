param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteHost,
    [string]$RemoteUser = "root",
    [string]$Port = "22",
    [string]$ProjectId = "AFP-Team",
    [string]$AgentId = "dev",
    [string]$AgentClass = "src.agents.factory_dev.AgentFactoryDevAgent",
    [string]$AmqpUrl = "amqp://afp:afp123@localhost:5672/",
    [switch]$UseKeyAuth
)

Write-Host "=== Agent Factory - Runtime Remoto ===" -ForegroundColor Cyan
Write-Host "Host:    $RemoteHost" -ForegroundColor Gray
Write-Host "Agent:   $AgentId ($AgentClass)" -ForegroundColor Gray
Write-Host "Projeto: $ProjectId" -ForegroundColor Gray

# Verificar SSH
$sshCmd = if ($UseKeyAuth) { "ssh" } else { "ssh" }
$authParam = if (-not $UseKeyAuth) { "-o PasswordAuthentication=yes" } else { "" }

# 1. Verificar conexao
Write-Host "Verificando conexao SSH..." -ForegroundColor Yellow
$testResult = & $sshCmd -p $Port -o ConnectTimeout=5 -o BatchMode=yes $authParam "$RemoteUser@$RemoteHost" "echo OK" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Conexao SSH falhou. Verifique as credenciais." -ForegroundColor Red
    exit 1
}

# 2. Verificar Python no remoto
Write-Host "Verificando requisitos remotos..." -ForegroundColor Yellow
$pyResult = & $sshCmd -p $Port "$RemoteUser@$RemoteHost" "python3 --version 2>&1 || python --version 2>&1" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python nao encontrado no remoto." -ForegroundColor Red
    exit 1
}
Write-Host "Remoto: $pyResult" -ForegroundColor Green

# 3. Verificar/instalar pika no remoto
Write-Host "Verificando pika (Python RabbitMQ)..." -ForegroundColor Yellow
& $sshCmd -p $Port "$RemoteUser@$RemoteHost" "pip3 install pika -q 2>&1 || pip install pika -q 2>&1"

# 4. Sincronizar codigo (opcional - se o remoto nao tiver o repo)
$remoteDir = "/opt/agent-factory"
Write-Host "Verificando diretorio remoto..." -ForegroundColor Yellow
$dirResult = & $sshCmd -p $Port "$RemoteUser@$RemoteHost" "test -d $remoteDir && echo EXISTS || echo MISSING" 2>&1
if ($dirResult -match "MISSING") {
    Write-Host "Diretorio remoto nao encontrado. Use rsync ou clone manual." -ForegroundColor Yellow
    Write-Host "Criando diretorio e copiando codigo via rsync..." -ForegroundColor Yellow
    & $sshCmd -p $Port "$RemoteUser@$RemoteHost" "mkdir -p $remoteDir"
    # Rsync do diretorio atual (excluindo .git, __pycache__, etc.)
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    rsync -avz --delete --exclude ".git" --exclude "__pycache__" --exclude "*.pyc" --exclude ".agent-factory" -e "ssh -p $Port" "$root/" "$RemoteUser@$RemoteHost:$remoteDir/"
    Write-Host "Codigo sincronizado." -ForegroundColor Green
}

# 5. Iniciar runtime remoto
Write-Host "=== Iniciando runtime remoto para $AgentId ===" -ForegroundColor Cyan
$startCmd = "cd $remoteDir && nohup python3 -m src.agents.runtime $AgentClass $AgentId $ProjectId '' '$AmqpUrl' > /tmp/agent-$AgentId.log 2>&1 & echo PID: \$!"
Write-Host "Comando: $startCmd" -ForegroundColor Gray

$result = & $sshCmd -p $Port "$RemoteUser@$RemoteHost" $startCmd 2>&1
Write-Host "Resultado: $result" -ForegroundColor Green

Write-Host ""
Write-Host "Runtime remoto iniciado! Logs: ssh $RemoteUser@$RemoteHost 'tail -f /tmp/agent-$AgentId.log'" -ForegroundColor Green
Write-Host "Management UI: http://localhost:15672 (afp/afp123)" -ForegroundColor Green
