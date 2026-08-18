param(
    [switch]$Stop,
    [switch]$HealthCheck,
    [switch]$Restart,
    [switch]$Repair,
    [string]$ProjectId = "demo-onboarding"
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = "$Root\.agent-factory\logs"
$PidFile = "$Root\.agent-factory\afp.pid"
$ManifestFile = "$Root\.agent-factory\afp.manifest.json"

New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction SilentlyContinue | Out-Null

$ProcessDefs = [ordered]@{
    dashboard   = @{ Args = "$Root\_run_dashboard.py" }
    mcp         = @{ Args = "-m src.mcp.server --sse --port 8081" }
    coordinator = @{ Args = "-m src.agents.runtime src.agents.coordinator.AgentFactoryCoordinator coordenador $ProjectId" }
    "runtime-dev" = @{ Args = "-m src.agents.runtime src.agents.worker.DeclarativeWorker dev $ProjectId" }
}

function Write-AfpLogLine {
    param([string]$Path, [string]$Line)
    try {
        Add-Content -Path $Path -Value $Line -Encoding UTF8 -ErrorAction Stop
    } catch {
        $alt = "$Path.$([Guid]::NewGuid().ToString('N').Substring(0,8))"
        Add-Content -Path $alt -Value $Line -Encoding UTF8
    }
}

function Stop-AfpStack {
    if (Test-Path $PidFile) {
        Get-Content $PidFile | ForEach-Object {
            if ($_ -match '^\d+$') {
                try { Stop-Process -Id ([int]$_) -Force -ErrorAction SilentlyContinue } catch {}
            }
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $ManifestFile) {
        Remove-Item $ManifestFile -Force -ErrorAction SilentlyContinue
    }
    Get-Process -Name python, pythonw -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmd = $_.CommandLine -join ' '
            if ($cmd -match 'src\.(dashboard\.server|mcp\.server|agents\.runtime)|_run_dashboard\.py') {
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
}

function Test-AfpProcessAlive {
    param([int]$ProcessId)
    try {
        $p = Get-Process -Id $ProcessId -ErrorAction Stop
        return $null -ne $p
    } catch {
        return $false
    }
}

function Invoke-AfpHealthCheck {
    param([switch]$Quiet)
    $script:HealthExit = 0
    $hcScript = Join-Path $Root "healthcheck.ps1"
    if (Test-Path $hcScript) {
        & $hcScript
        $script:HealthExit = $LASTEXITCODE
    } else {
        python (Join-Path $Root "healthcheck.py")
        $script:HealthExit = $LASTEXITCODE
    }
    return $script:HealthExit
}

function Start-AfpProcess {
    param([string]$Name, [string]$Arguments)
    $logFile = "$LogDir\$Name.log"
    $errFile = "$LogDir\$Name.err"
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-AfpLogLine $logFile "=== Started at $stamp ==="
    Write-AfpLogLine $errFile "=== Started at $stamp ==="
    $proc = Start-Process -FilePath python.exe -ArgumentList $Arguments -WorkingDirectory $Root `
        -WindowStyle Hidden -RedirectStandardOutput $logFile -RedirectStandardError $errFile -PassThru
    Start-Sleep -Milliseconds 250
    if ($proc.HasExited) {
        $exitCode = $proc.ExitCode
        $err = Get-Content $errFile -Raw -ErrorAction SilentlyContinue
        Write-Host "[FAIL] $Name exit=$exitCode" -ForegroundColor Red
        if ($err) { Write-Host "  STDERR: $($err.Substring(0,[Math]::Min(500,$err.Length)))" -ForegroundColor Red }
    } else {
        Write-Host "[OK] $Name (PID $($proc.Id))" -ForegroundColor Green
    }
    return [pscustomobject]@{ Name = $Name; Pid = $proc.Id; Alive = -not $proc.HasExited }
}

function Save-AfpManifest {
    param([array]$Entries)
    $manifest = @{}
    foreach ($e in $Entries) { $manifest[$e.Name] = $e.Pid }
    $manifest | ConvertTo-Json | Out-File $ManifestFile -Encoding UTF8
    ($Entries | ForEach-Object { $_.Pid }) | Out-File $PidFile -Encoding ASCII
}

function Start-AfpStack {
    Stop-AfpStack
    Start-Sleep -Seconds 2
    Write-Output "Iniciando AFP..."
    $entries = @()
    foreach ($name in $ProcessDefs.Keys) {
        $entries += Start-AfpProcess -Name $name -Arguments $ProcessDefs[$name].Args
        if ($name -eq "mcp") { Start-Sleep -Seconds 1 }
        elseif ($name -eq "coordinator") { Start-Sleep -Seconds 1 }
        else { Start-Sleep -Milliseconds 500 }
    }
    Save-AfpManifest $entries
    Write-Output "---"
    Write-Output "AFP rodando. Logs em: $LogDir"
}

function Repair-AfpStack {
    if (-not (Test-Path $ManifestFile)) {
        Write-Host "[REPAIR] Manifest ausente — reiniciando stack completa." -ForegroundColor Yellow
        Start-AfpStack
        return
    }
    $manifest = Get-Content $ManifestFile -Raw | ConvertFrom-Json
    $restarted = 0
    foreach ($name in $ProcessDefs.Keys) {
        $procId = [int]$manifest.$name
        if ($procId -gt 0 -and (Test-AfpProcessAlive $procId)) { continue }
        Write-Host "[REPAIR] Reiniciando $name (PID anterior: $procId)..." -ForegroundColor Yellow
        $entry = Start-AfpProcess -Name $name -Arguments $ProcessDefs[$name].Args
        $manifest.$name = $entry.Pid
        $restarted++
        Start-Sleep -Milliseconds 400
    }
    if ($restarted -gt 0) {
        $entries = foreach ($name in $ProcessDefs.Keys) {
            [pscustomobject]@{ Name = $name; Pid = [int]$manifest.$name }
        }
        Save-AfpManifest $entries
        Write-Host "[REPAIR] $restarted processo(s) reiniciado(s)." -ForegroundColor Green
    } else {
        Write-Host "[REPAIR] Todos os processos estao vivos." -ForegroundColor Green
    }
}

if ($Stop) {
    Stop-AfpStack
    Write-Output "AFP parado"
    return
}

if ($HealthCheck) {
    exit (Invoke-AfpHealthCheck)
}

if ($Restart) {
    Stop-AfpStack
    Start-Sleep -Seconds 2
    Start-AfpStack
    Start-Sleep -Seconds 3
    $code = Invoke-AfpHealthCheck
    if ($code -ne 0) {
        Write-Host "Healthcheck falhou apos restart — tentando repair..." -ForegroundColor Yellow
        Repair-AfpStack
        Start-Sleep -Seconds 2
        exit (Invoke-AfpHealthCheck)
    }
    exit 0
}

if ($Repair) {
    Repair-AfpStack
    Start-Sleep -Seconds 2
    exit (Invoke-AfpHealthCheck)
}

# Default: start stack + healthcheck + auto-repair se necessario
Start-AfpStack
Start-Sleep -Seconds 3
$code = Invoke-AfpHealthCheck
if ($code -ne 0) {
    Write-Host "Healthcheck falhou — executando repair automatico..." -ForegroundColor Yellow
    Repair-AfpStack
    Start-Sleep -Seconds 2
    Invoke-AfpHealthCheck | Out-Null
}
