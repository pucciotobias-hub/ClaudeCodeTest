<#
.SYNOPSIS
    Corre el estudio diario de GGAL ADR en TradingView via Claude Code headless.

.DESCRIPTION
    1. Se asegura de que Chrome este corriendo con CDP en el puerto 9222.
    2. Invoca `claude -p` con la receta de scripts/ggal_estudio_prompt.md.
    3. Claude redibuja los niveles, lee EMA/RSI/macro, escribe el informe en
       estudios/ggal/<fecha>-<turno>.md y lo commitea.

    Requiere una sesion de escritorio activa: Chrome tiene que poder renderizar.
    Si la maquina esta bloqueada o con sesion cerrada, el chart no repinta.

.PARAMETER Turno
    'apertura' (pre-mercado) o 'cierre' (post-mercado).

.EXAMPLE
    .\ggal_estudio.ps1 -Turno apertura
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('apertura', 'cierre')]
    [string]$Turno
)

$ErrorActionPreference = 'Stop'

# --- Rutas -----------------------------------------------------------------
$RepoDir     = Split-Path -Parent $PSScriptRoot
$PromptFile  = Join-Path $PSScriptRoot 'ggal_estudio_prompt.md'
$RelanzarScript = Join-Path $PSScriptRoot 'relanzar_chrome_cdp.ps1'
$LogDir      = Join-Path $RepoDir 'logs'
$LogFile     = Join-Path $LogDir 'ggal_estudio.log'
$ClaudeExe   = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
$McpConfig   = Join-Path $env:USERPROFILE '.mcp.json'
$ChromeExe   = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$CdpProfile  = Join-Path $env:USERPROFILE 'tv-cdp-profile'
$ChartUrl    = 'https://www.tradingview.com/chart/pzxwEAwm/'
$CdpPort     = 9222

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = "{0} | {1,-5} | {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Add-Content -Path $LogFile -Value $line -Encoding utf8
    Write-Output $line
}

function Test-Cdp {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$CdpPort/json/version" -TimeoutSec 3
        return [bool]$r.Browser
    } catch { return $false }
}

# --- 1. Preflight ----------------------------------------------------------
Write-Log "=== INICIO estudio GGAL - turno: $Turno ==="

foreach ($req in @(@{p = $ClaudeExe; n = 'claude.exe' }, @{p = $PromptFile; n = 'prompt' }, @{p = $McpConfig; n = '.mcp.json' }, @{p = $RelanzarScript; n = 'relanzar_chrome_cdp.ps1' })) {
    if (-not (Test-Path $req.p)) {
        Write-Log "No se encontro $($req.n) en $($req.p). Abortando." 'ERROR'
        exit 1
    }
}

# --- 2. Chrome con CDP -----------------------------------------------------
# La logica vive en relanzar_chrome_cdp.ps1 porque Claude tambien la necesita si
# el CDP se cae a mitad de la corrida. El script es idempotente.
Write-Log "Verificando Chrome/CDP..."
$salidaChrome = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RelanzarScript
$salidaChrome | ForEach-Object { Write-Log "  chrome: $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Log "No se pudo levantar Chrome con CDP. Abortando." 'ERROR'
    exit 1
}

# --- 3. Armar el prompt ----------------------------------------------------
$fecha  = Get-Date -Format 'yyyy-MM-dd'
$hora   = Get-Date -Format 'HH:mm'
$receta = Get-Content $PromptFile -Raw

$prompt = @"
FECHA: $fecha
HORA LOCAL (ART): $hora
TURNO: $Turno
ARCHIVO DE SALIDA: estudios/ggal/$fecha-$Turno.md

Corrida automatica y desatendida. Segui la receta de abajo de punta a punta y
no pidas confirmacion de nada.

$receta
"@

# --- 4. Correr Claude ------------------------------------------------------
Write-Log "Invocando Claude Code (headless)..."

$allowed = @(
    'mcp__tradingview'
    'Read'
    'Write'
    'Edit'
    'Glob'
    'Grep'
    'Bash(git add *)'
    'Bash(git commit *)'
    'Bash(git push *)'
    'Bash(git status*)'
    'Bash(git log*)'
    'Bash(git diff*)'
    'Bash(python *)'
    'Bash(ls *)'
    'Bash(cat *)'
    'Bash(mkdir *)'
    # Sin esto, si el CDP se cae a mitad del estudio Claude no puede recuperarlo y
    # el informe sale parcial (paso el 2026-09-09: se perdio el macro y el
    # retrazado). El patron apunta solo al script de relanzamiento.
    'Bash(powershell*relanzar_chrome_cdp.ps1*)'
) -join ','

Push-Location $RepoDir
try {
    $out = $prompt | & $ClaudeExe -p `
        --model claude-opus-5 `
        --mcp-config $McpConfig `
        --permission-mode acceptEdits `
        --allowedTools $allowed 2>&1 | Out-String
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

Add-Content -Path $LogFile -Value $out -Encoding utf8

if ($code -ne 0) {
    Write-Log "Claude salio con codigo $code." 'ERROR'
    exit $code
}

$informe = Join-Path $RepoDir "estudios\ggal\$fecha-$Turno.md"
if (Test-Path $informe) {
    Write-Log "OK. Informe: $informe"
} else {
    Write-Log "Claude termino OK pero no aparecio $informe." 'WARN'
}

Write-Log "=== FIN estudio GGAL - turno: $Turno ==="
