<#
.SYNOPSIS
    Corre el estudio diario de GGAL ADR en TradingView via Claude Code headless,
    o la auditoria semanal de esos estudios.

.DESCRIPTION
    1. Se asegura de que Chrome este corriendo con CDP en el puerto 9222.
    2. Invoca `claude -p` con la receta de scripts/ggal_estudio_prompt.md.
    3. Claude redibuja los niveles, lee EMA/RSI/macro, escribe el informe en
       estudios/ggal/<fecha>-<turno>.md y lo commitea.

    Con -Turno auditoria usa la receta de scripts/ggal_auditoria_prompt.md: baja
    las barras de GGAL, contrasta los estudios de la semana contra el precio y
    escribe estudios/ggal/auditorias/<fecha>.md.

    Con -Turno mediodia corre la misma receta que apertura/cierre, con el
    agregado de la lectura intradia (seccion 6.bis de la receta). No tiene tarea
    programada: se dispara a mano cuando se quiere un panorama de mitad de rueda.

    Con -Turno semanal usa scripts/ggal_semanal_prompt.md: arma el reporte de la
    semana (numeros del feed, noticias macro, panorama) en
    estudios/ggal/semanal/<fecha>.json, lo incorpora a la pagina fija del semanal
    (scripts/ggal_semanal_incorporar.py) y la republica.

    Requiere una sesion de escritorio activa: Chrome tiene que poder renderizar.
    Si la maquina esta bloqueada o con sesion cerrada, el chart no repinta.

.PARAMETER Turno
    'apertura' (pre-mercado), 'mediodia' (mitad de rueda, a mano), 'cierre'
    (post-mercado), 'auditoria' (semanal) o 'semanal' (reporte de la semana con
    noticias y panorama).

.PARAMETER Forzar
    Corre aunque el informe de hoy ya exista o este fuera de la ventana horaria.
    Para correrlo a mano.

.EXAMPLE
    .\ggal_estudio.ps1 -Turno apertura
    .\ggal_estudio.ps1 -Turno cierre -Forzar
    .\ggal_estudio.ps1 -Turno mediodia
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('apertura', 'mediodia', 'cierre', 'auditoria', 'semanal')]
    [string]$Turno,

    [switch]$Forzar
)

$ErrorActionPreference = 'Stop'

# --- Rutas -----------------------------------------------------------------
$RepoDir     = Split-Path -Parent $PSScriptRoot
$Recetas     = @{ apertura = 'ggal_estudio_prompt.md'; mediodia = 'ggal_estudio_prompt.md'; cierre = 'ggal_estudio_prompt.md'; auditoria = 'ggal_auditoria_prompt.md'; semanal = 'ggal_semanal_prompt.md' }
$PromptFile  = Join-Path $PSScriptRoot $Recetas[$Turno]
$RelanzarScript = Join-Path $PSScriptRoot 'relanzar_chrome_cdp.ps1'
$LogDir      = Join-Path $RepoDir 'logs'
$LogFile     = Join-Path $LogDir 'ggal_estudio.log'
$ClaudeExe   = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
$McpConfig   = Join-Path $env:USERPROFILE '.mcp.json'
$ChromeExe   = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$CdpProfile  = Join-Path $env:USERPROFILE 'tv-cdp-profile'
$ChartUrl    = 'https://www.tradingview.com/chart/pzxwEAwm/'
$CdpPort     = 9222

# Tope de reloj real para claude -p. Va por reloj de pared, no por tiempo de CPU:
# si la maquina se suspende a mitad, al despertar ya esta pasado y se corta.
# Paso el 2026-09-17: la maquina se suspendio a las 19:31 con claude corriendo,
# desperto el 22-sep, y en esos 4 dias la tarea figuro "en ejecucion", asi que
# el Programador ignoro todos los disparos (MultipleInstances IgnoreNew): se
# perdieron los informes del 18, del 21 y la apertura del 22. El limite de 45 min
# de la tarea no lo corto. Tiene que quedar debajo de esos 45.
$TopeMinutos = 40

# Ventana en la que cada turno tiene sentido (hora ART). Fuera de ella la corrida
# se saltea: el cierre del 10-sep corrio a las 00:55 del 11 y salio con fecha 11,
# y el del 15-sep corrio 16 h tarde en paralelo con la apertura del 16 y se
# pisaron los dibujos. La auditoria no tiene ventana. El semanal no puede pisarse
# con la apertura (usan el mismo chart), por eso sus disparos son 09:30 y 12:00.
$Ventanas = @{
    apertura = @{ Desde = '10:00'; Hasta = '16:30' }
    mediodia = @{ Desde = '11:00'; Hasta = '16:45' }
    cierre   = @{ Desde = '17:00'; Hasta = '23:59' }
    semanal  = @{ Desde = '09:00'; Hasta = '16:30' }
}

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

$fecha  = Get-Date -Format 'yyyy-MM-dd'
$hora   = Get-Date -Format 'HH:mm'
$salida = switch ($Turno) {
    'auditoria' { "estudios/ggal/auditorias/$fecha.md" }
    'semanal'   { "estudios/ggal/semanal/$fecha.json" }
    default     { "estudios/ggal/$fecha-$Turno.md" }
}

# Cada turno tiene varios disparos (ver install_ggal_tasks.ps1): si uno muere en
# el despertar de la maquina, el siguiente lo cubre. Los que llegan despues de
# una corrida buena no tienen nada que hacer.
# "Hecho" es "commiteado", no "el archivo existe": el semanal copia la plantilla
# al archivo de salida al principio, y una corrida que muere a mitad lo dejaba ahi
# y los reintentos se salteaban (paso el 2026-09-28).
# Sin --error-unmatch: con ErrorActionPreference Stop, PowerShell 5.1 convierte el
# stderr de git en excepcion y el wrapper moria sin loguear justo cuando habia
# trabajo que hacer (paso del 28 al 29-sep: cierre del 28, aperturas y cierre del
# 29). ls-files a secas no escribe en stderr: devuelve la ruta o nada.
if (-not $Forzar) {
    $trackeado = & git -C $RepoDir ls-files -- $salida
    if ($trackeado) {
        Write-Log "Ya esta commiteado $salida. Nada que hacer."
        exit 0
    }
    $v = $Ventanas[$Turno]
    if ($v -and ($hora -lt $v.Desde -or $hora -gt $v.Hasta)) {
        Write-Log "Fuera de ventana ($hora, el turno $Turno va de $($v.Desde) a $($v.Hasta)). Se saltea; para correrlo igual, -Forzar." 'WARN'
        exit 0
    }
}

# Un solo estudio a la vez: todos manejan el mismo chart. El 2026-09-28 la maquina
# durmio hasta las 10:20 y el semanal de las 09:30 se disparo al despertar, en
# paralelo con la apertura. Si el chart esta ocupado se sale sin hacer nada y el
# reintento siguiente lo cubre (esperar no sirve: el tope de la tarea es 45 min).
$candado = New-Object System.Threading.Mutex($false, 'Local\GgalEstudioChart')
# AbandonedMutexException = el duenio anterior murio sin soltarlo: el candado es nuestro.
$libre = try { $candado.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $true }
if (-not $libre) {
    Write-Log "Hay otro estudio GGAL corriendo sobre el chart. Se saltea; lo cubre el reintento siguiente." 'WARN'
    exit 0
}

# --- 1.a Oficina 3D ---------------------------------------------------------
# Solo por diversion: oficina/index.html muestra a los agentes trabajando. Aca se
# le avisa quien trabaja y en que paso va, y se abre si nadie la esta mirando.
# Nada de esto puede tirar abajo el estudio: todo va en try/catch.
$OficinaDir    = Join-Path $RepoDir 'oficina'
$agenteOficina = if ($Turno -eq 'semanal') { 'redactor' } else { 'analista' }
$desdeOficina  = Get-Date -Format 's'
function Set-Oficina {
    param([string]$Paso, [bool]$Activo = $true, [string]$Resultado = $null)
    try {
        $e = [ordered]@{ activo = $Activo; agente = $agenteOficina; turno = $Turno; paso = $Paso; desde = $desdeOficina; pid = $PID; resultado = $Resultado }
        [IO.File]::WriteAllText((Join-Path $OficinaDir 'estado.json'), ($e | ConvertTo-Json -Compress), (New-Object System.Text.UTF8Encoding $false))
    } catch { Write-Log "Oficina: no se pudo escribir el estado ($_)" 'WARN' }
}
Set-Oficina 'preparando'
try { & (Join-Path $OficinaDir 'abrir_oficina.ps1') -SiNadieMira | ForEach-Object { Write-Log "Oficina: $_" } }
catch { Write-Log "Oficina: no se pudo abrir ($_)" 'WARN' }

# --- 1.b Bloquear la suspension -------------------------------------------
# La corrida tarda ~12 min y nadie toca el teclado mientras tanto, asi que el
# temporizador de inactividad de Windows se cumple siempre y se lleva puesto el
# proceso. Paso el 2026-09-10: a las 10:27:28 la maquina entro en espera moderna
# por "Idle Timeout" con claude -p corriendo y la tarea murio con 0xC000013A.
# ES_CONTINUOUS mantiene el pedido vivo hasta que lo soltemos o muera el proceso,
# asi que una salida temprana tampoco deja la maquina sin dormir.
# ES_DISPLAY_REQUIRED va incluido a proposito: Chrome tiene que poder renderizar
# el chart, asi que la pantalla queda prendida mientras dura el estudio.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class GgalPower {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
'@

$ES_CONTINUOUS       = [uint32]'0x80000000'
$ES_SYSTEM_REQUIRED  = [uint32]'0x00000001'
$ES_DISPLAY_REQUIRED = [uint32]'0x00000002'

if ([GgalPower]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_DISPLAY_REQUIRED) -eq 0) {
    Write-Log "No se pudo bloquear la suspension; si la maquina se duerme la corrida muere." 'WARN'
} else {
    Write-Log "Suspension bloqueada mientras dure la corrida."
}

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
Set-Oficina 'chrome'
$salidaChrome = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RelanzarScript
$salidaChrome | ForEach-Object { Write-Log "  chrome: $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Log "No se pudo levantar Chrome con CDP. Abortando." 'ERROR'
    exit 1
}

# --- 3. Armar el prompt ----------------------------------------------------
$receta = Get-Content $PromptFile -Raw

$prompt = @"
FECHA: $fecha
HORA LOCAL (ART): $hora
TURNO: $Turno
ARCHIVO DE SALIDA: $salida

Corrida automatica y desatendida. Segui la receta de abajo de punta a punta y
no pidas confirmacion de nada.

$receta
"@

# --- 4. Correr Claude ------------------------------------------------------
Write-Log "Invocando Claude Code (headless)..."
Set-Oficina 'claude'

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
    # Solo el reporte semanal: noticias de la web y republicar la pagina.
    # (Hasta el 2026-10-05 cargaba un documento de Claude Docs que la pagina
    # leia al abrirse; una pagina publicada no puede leer Docs, falla self_only.)
    if ($Turno -eq 'semanal') { 'WebSearch'; 'WebFetch'; 'ToolSearch'; 'Artifact'; 'Skill' }
) -join ','

# Claude corre como proceso aparte (no con el pipe de siempre) para poder
# vigilarlo contra el reloj de pared y matarlo si pasa $TopeMinutos.
$tmpIn  = Join-Path $LogDir "claude_$Turno.in.txt"
$tmpOut = Join-Path $LogDir "claude_$Turno.out.txt"
$tmpErr = Join-Path $LogDir "claude_$Turno.err.txt"
[IO.File]::WriteAllText($tmpIn, $prompt, (New-Object System.Text.UTF8Encoding $false))

$argumentos = @(
    '-p'
    '--model', 'claude-opus-5-5'
    '--mcp-config', "`"$McpConfig`""
    '--permission-mode', 'acceptEdits'
    '--allowedTools', "`"$allowed`""
) -join ' '

$code = $null
try {
    $proc = Start-Process -FilePath $ClaudeExe -ArgumentList $argumentos `
        -WorkingDirectory $RepoDir -NoNewWindow -PassThru `
        -RedirectStandardInput $tmpIn -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr
    $null = $proc.Handle  # sin esto ExitCode puede quedar vacio con -PassThru
    $inicio = [DateTime]::UtcNow

    while (-not $proc.WaitForExit(15000)) {
        $min = ([DateTime]::UtcNow - $inicio).TotalMinutes
        if ($min -gt $TopeMinutos) {
            Write-Log ("Claude lleva {0:N0} min de reloj (tope {1}); se corta. Si el salto es grande, la maquina se suspendio a mitad." -f $min, $TopeMinutos) 'ERROR'
            # /T: claude levanta los servidores MCP como hijos.
            & taskkill.exe /PID $proc.Id /T /F | Out-Null
            $proc.WaitForExit(10000) | Out-Null
            $code = 124
            break
        }
    }
    if ($null -eq $code) { $code = $proc.ExitCode }
} finally {
    [GgalPower]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
    Write-Log "Suspension desbloqueada."
    Set-Oficina 'fin' $false $(if ($code -eq 0) { 'ok' } else { 'error' })
    $candado.ReleaseMutex()
    foreach ($f in @($tmpOut, $tmpErr)) {
        if (Test-Path $f) { Add-Content -Path $LogFile -Value (Get-Content $f -Raw -Encoding utf8) -Encoding utf8 }
    }
    Remove-Item $tmpIn, $tmpOut, $tmpErr -ErrorAction SilentlyContinue
}

# Aviso por Telegram (scripts/telegram_aviso.py). Nunca tumba la corrida: si no
# hay credenciales, red o python, queda una linea en el log y se sigue. El script
# escribe solo en stdout, porque con ErrorActionPreference Stop el stderr de un
# ejecutable se vuelve excepcion.
function Send-Aviso {
    param([string[]]$Argumentos)
    try {
        $py = Get-Command python.exe -All -ErrorAction SilentlyContinue |
            Sort-Object { $_.Source -like '*WindowsApps*' } | Select-Object -First 1
        if (-not $py) { Write-Log 'Aviso de Telegram: no se encontro python.exe.' 'WARN'; return }
        $r = & $py.Source (Join-Path $PSScriptRoot 'telegram_aviso.py') @Argumentos
        Write-Log "Aviso: $r"
    } catch {
        Write-Log "Aviso de Telegram fallo: $($_.Exception.Message)" 'WARN'
    }
}

if ($code -ne 0) {
    Write-Log "Claude salio con codigo $code." 'ERROR'
    Send-Aviso @('--texto', "GGAL $Turno ${fecha}: la corrida fallo (codigo $code). Ver logs/ggal_estudio.log.")
    exit $code
}

$informe = Join-Path $RepoDir $salida
if (Test-Path $informe) {
    Write-Log "OK. Informe: $informe"
    Send-Aviso @('--informe', $informe)
} else {
    Write-Log "Claude termino OK pero no aparecio $informe." 'WARN'
    Send-Aviso @('--texto', "GGAL $Turno ${fecha}: Claude termino OK pero no aparecio el informe.")
}

Write-Log "=== FIN estudio GGAL - turno: $Turno ==="
# Explicito: sin esto la tarea hereda el codigo del ultimo ejecutable, y el aviso
# de Telegram sale con 2 cuando no hay credenciales.
exit 0
