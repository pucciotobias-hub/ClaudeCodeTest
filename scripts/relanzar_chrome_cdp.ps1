<#
.SYNOPSIS
    Levanta (o relevanta) Chrome con CDP en el puerto 9222 apuntando al chart de TradingView.

.DESCRIPTION
    Lo usan dos cosas:
      - ggal_estudio.ps1, en el preflight.
      - El propio Claude durante la corrida, si el CDP se cae a mitad del estudio
        (pasa: un chart_set_symbol puede tirar "WebSocket connection closed").

    Es idempotente: si el CDP ya responde no toca nada y sale 0.

    tv_launch y launch-tv.bat NO sirven en esta maquina (es TradingView web en
    Chrome, no la app de escritorio). Start-Process es lo unico estable.

.PARAMETER Force
    Mata y relanza aunque el CDP este respondiendo.

.EXAMPLE
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\relanzar_chrome_cdp.ps1
#>
[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$ChromeExe  = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$CdpProfile = Join-Path $env:USERPROFILE 'tv-cdp-profile'
$ChartUrl   = 'https://www.tradingview.com/chart/pzxwEAwm/'
$CdpPort    = 9222

function Test-Cdp {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$CdpPort/json/version" -TimeoutSec 3
        return [bool]$r.Browser
    } catch { return $false }
}

if ((Test-Cdp) -and -not $Force) {
    Write-Output "CDP ya escuchando en $CdpPort."
    exit 0
}

if (-not (Test-Path $ChromeExe)) {
    Write-Output "ERROR: no se encontro Chrome en $ChromeExe."
    exit 1
}

# Si quedo una instancia zombi del perfil CDP, un Start-Process nuevo solo le pasa
# la URL y nunca bindea el puerto. Hay que matarla primero. El filtro por ruta del
# perfil deja intacto el Chrome normal del usuario.
$zombis = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*$CdpProfile*" }
if ($zombis) {
    Write-Output "Matando $(@($zombis).Count) proceso(s) del perfil CDP."
    foreach ($z in $zombis) { Stop-Process -Id $z.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
}

Start-Process -FilePath $ChromeExe -ArgumentList `
    "--remote-debugging-port=$CdpPort", `
    "--user-data-dir=$CdpProfile", `
    '--no-first-run', `
    '--no-default-browser-check', `
    $ChartUrl

foreach ($i in 1..20) {
    Start-Sleep -Seconds 3
    if (Test-Cdp) {
        Write-Output "CDP arriba despues de $($i * 3)s."
        # Margen para que TradingView cargue el layout y los datos del chart.
        Start-Sleep -Seconds 20
        Write-Output "Chart cargado. Listo."
        exit 0
    }
}

Write-Output "ERROR: el CDP no levanto en 60s."
exit 1
