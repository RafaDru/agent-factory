# Inicia o icone AFP na bandeja do sistema (sem janela de console)
param(
    [switch]$Restart
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$TrayScript = Join-Path $Root "scripts\afp_tray.py"

if (-not (Test-Path $TrayScript)) {
    Write-Error "Nao encontrado: $TrayScript"
    exit 1
}

function Get-AfpTrayProcesses {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match 'afp_tray\.py' }
}

$existing = @(Get-AfpTrayProcesses)
if ($existing.Count -gt 0 -and -not $Restart) {
    Write-Host "AFP System Tray ja esta rodando ($($existing.Count) instancia(s), PID: $($existing.ProcessId -join ', '))."
    Write-Host "Use: .\start_afp_tray.ps1 -Restart  para reiniciar com icone atualizado."
    exit 0
}

if ($Restart -and $existing.Count -gt 0) {
    Write-Host "Encerrando $($existing.Count) instancia(s) anterior(es)..."
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Milliseconds 500
}

# Dependencias
$req = Join-Path $Root "scripts\requirements-tray.txt"
if (Test-Path $req) {
    python -m pip install -r $req -q 2>$null
}

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonw = (Get-Command python.exe).Source
}

Start-Process -FilePath $pythonw -ArgumentList "`"$TrayScript`"" -WorkingDirectory $Root -WindowStyle Hidden
Write-Host "AFP System Tray iniciado (pythonw). Icone ao lado do relogio."
Write-Host "Para encerrar: botao direito no icone > Sair"
