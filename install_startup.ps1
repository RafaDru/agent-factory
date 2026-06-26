# ============================================
REM Agent Factory - Inicialização com Windows (PowerShell)
REM ============================================
REM Este script inicia o Agent Factory automaticamente
REM quando o Windows é iniciado.
REM
REM Para instalar:
REM 1. Abra PowerShell como administrador
REM 2. Execute: .\install_startup.ps1
REM
REM Para remover:
REM 1. Abra PowerShell como administrador
REM 2. Execute: .\uninstall_startup.ps1
REM ============================================

# Configurações
$AgentFactoryPath = "C:\Users\rafae\agent-factory"
$ScriptName = "AgentFactory"
$TaskName = "AgentFactoryStartup"

# Verificar se o Agent Factory existe
if (-Not (Test-Path $AgentFactoryPath)) {
    Write-Host "ERRO: Agent Factory não encontrado em $AgentFactoryPath"
    exit 1
}

# Criar tarefa agendada para iniciar com o Windows
$action = New-ScheduledTaskAction -Execute "python" -Argument "start_dashboard.py" -WorkingDirectory $AgentFactoryPath
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Registrar tarefa agendada
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force

Write-Host "Agent Factory configurado para iniciar com o Windows!"
Write-Host "Para iniciar agora, execute: python start_dashboard.py"
Write-Host "Dashboard estará disponível em: http://localhost:8080?project=pta"
