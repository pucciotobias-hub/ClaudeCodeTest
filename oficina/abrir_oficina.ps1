<#
.SYNOPSIS
    Abre la oficina 3D de los agentes GGAL en el navegador.

.DESCRIPTION
    Levanta oficina/servidor.py en segundo plano si no esta corriendo (queda
    vivo, es liviano) y abre http://127.0.0.1:8765/ en el navegador por defecto.
    Lo usa el wrapper de los estudios al arrancar cada corrida, y se puede
    correr a mano cuando quieras ver a los agentes tomando cafe.

.PARAMETER SiNadieMira
    No abre otra pestania si ya hay una mirando la oficina. Lo pasa el wrapper
    para no llenar el navegador de pestanias en cada corrida.

.EXAMPLE
    .\oficina\abrir_oficina.ps1
#>
[CmdletBinding()]
param([switch]$SiNadieMira)

$ErrorActionPreference = 'Stop'
$Url      = 'http://127.0.0.1:8765/'
$Servidor = Join-Path $PSScriptRoot 'servidor.py'

function Test-Servidor {
    try { Invoke-RestMethod -Uri "${Url}mirando" -TimeoutSec 2 } catch { $null }
}

$r = Test-Servidor
if (-not $r) {
    # El pythonw de WindowsApps es un alias que a veces no arranca: preferir el real.
    $pyw = Get-Command pythonw.exe -All -ErrorAction SilentlyContinue |
        Sort-Object { $_.Source -like '*WindowsApps*' } | Select-Object -First 1
    if (-not $pyw) { throw 'No se encontro pythonw.exe' }
    Start-Process -FilePath $pyw.Source -ArgumentList "`"$Servidor`"" -WindowStyle Hidden
    foreach ($i in 1..20) {
        Start-Sleep -Milliseconds 250
        $r = Test-Servidor
        if ($r) { break }
    }
    if (-not $r) { throw 'El servidor de la oficina no arranco' }
}

if ($SiNadieMira -and $r.mirando) {
    Write-Output 'La oficina ya esta abierta.'
    exit 0
}
Start-Process $Url
Write-Output "Oficina abierta en $Url"
