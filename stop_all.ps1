Write-Host "=== Parando servicos ===" -ForegroundColor Cyan

# Para runtimes Python (agents)
Get-Process -Name "python" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "src\.agents\.runtime" -or $_.CommandLine -match "runtime" } |
    ForEach-Object { Write-Host "  Parando runtime PID $($_.Id)"; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }

# Para servidores
Get-Process -Name "python" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "src\.server\.main|src\.dashboard\.server" } |
    ForEach-Object { Write-Host "  Parando servidor PID $($_.Id)"; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }

# Para RabbitMQ
docker compose down rabbitmq 2>$null
Write-Host "Container RabbitMQ parado" -ForegroundColor DarkYellow

Write-Host "Pronto!" -ForegroundColor Green
