# Sobe RabbitMQ via Docker Compose
docker compose up -d rabbitmq

Write-Host "Aguardando RabbitMQ ficar saudavel..." -ForegroundColor Cyan
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    $result = docker compose exec rabbitmq rabbitmq-diagnostics check_port_connectivity 2>$null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if ($ready) {
    Write-Host "RabbitMQ pronto! Management UI: http://localhost:15672 (afp/afp123)" -ForegroundColor Green
} else {
    Write-Host "Timeout aguardando RabbitMQ. Verifique o container." -ForegroundColor Yellow
}
