param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,
    [Parameter(Mandatory = $true)]
    [string]$ProjectName,
    [string]$Description = "Projeto registrado via scaffold AFP",
    [string]$WorkingDir = "",
    [string]$TeamId = "",
    [switch]$Force
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TemplateDir = Join-Path $Root "contexts\_template"
$TargetDir = Join-Path $Root "contexts\$ProjectId"

if (-not (Test-Path $TemplateDir)) {
    Write-Error "Template nao encontrado: $TemplateDir"
    exit 1
}

if ((Test-Path $TargetDir) -and -not $Force) {
    Write-Error "Projeto ja existe: $TargetDir (use -Force para sobrescrever arquivos do template)"
    exit 1
}

if (-not $WorkingDir) {
    $WorkingDir = (Join-Path $Root "contexts\$ProjectId" | Resolve-Path -ErrorAction SilentlyContinue)
    if (-not $WorkingDir) { $WorkingDir = (Join-Path $Root "contexts\$ProjectId") }
}
if (-not $TeamId) { $TeamId = "$ProjectId-Team" }
$TeamName = "$ProjectName Team"

New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
Copy-Item -Path "$TemplateDir\*" -Destination $TargetDir -Recurse -Force

$replacements = @{
    "{{PROJECT_ID}}"   = $ProjectId
    "{{PROJECT_NAME}}" = $ProjectName
    "{{TEAM_ID}}"      = $TeamId
    "{{TEAM_NAME}}"    = $TeamName
    "{{DESCRIPTION}}"  = $Description
    "{{WORKING_DIR}}"  = $WorkingDir.Replace('\', '/')
}

Get-ChildItem $TargetDir -Recurse -File | ForEach-Object {
    $content = Get-Content $_.FullName -Raw -Encoding UTF8
    foreach ($key in $replacements.Keys) {
        $content = $content.Replace($key, $replacements[$key])
    }
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8 -NoNewline
}

Write-Host "Projeto criado em: $TargetDir" -ForegroundColor Green
Write-Host "  project.json + coordenador/ + dev/"
Write-Host "Proximo passo: reinicie AFP ou aguarde auto-discovery; depois run_objective('$ProjectId', ...)"
