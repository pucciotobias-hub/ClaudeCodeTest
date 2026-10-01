<#
.SYNOPSIS
    Abre el tablero de tasas de A3 en el navegador.

.DESCRIPTION
    Levanta tasas/servidor.py en segundo plano si no esta corriendo (queda vivo:
    mantiene la conexion con A3 y guarda la foto diaria de interes abierto en
    tasas/historia/) y abre http://127.0.0.1:8766/ en el navegador por defecto.

.EXAMPLE
    .\tasas\abrir_tasas.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Url      = 'http://127.0.0.1:8766/'
$Servidor = Join-Path $PSScriptRoot 'servidor.py'

function Test-Servidor {
    try { Invoke-RestMethod -Uri "${Url}datos" -TimeoutSec 3 } catch { $null }
}

if (-not (Test-Servidor)) {
    # El pythonw de WindowsApps es un alias que a veces no arranca: preferir el real.
    $pyw = Get-Command pythonw.exe -All -ErrorAction SilentlyContinue |
        Sort-Object { $_.Source -like '*WindowsApps*' } | Select-Object -First 1
    if (-not $pyw) { throw 'No se encontro pythonw.exe' }
    Start-Process -FilePath $pyw.Source -ArgumentList "`"$Servidor`"" -WindowStyle Hidden
    $ok = $false
    foreach ($i in 1..40) {
        Start-Sleep -Milliseconds 250
        if (Test-Servidor) { $ok = $true; break }
    }
    if (-not $ok) { throw 'El servidor de tasas no arranco' }
}

Start-Process $Url
Write-Output "Tablero de tasas abierto en $Url"
