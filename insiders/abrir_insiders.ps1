<#
.SYNOPSIS
    Abre el tablero de compras de directivos (insider tracker) en el navegador.

.DESCRIPTION
    Levanta insiders/servidor.py en segundo plano si no esta corriendo (mantiene
    al dia la base de Form 4 de la SEC: la primera vez baja 30 dias, unos 20
    minutos) y abre http://127.0.0.1:8769/ en el navegador por defecto.

.EXAMPLE
    .\insiders\abrir_insiders.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Url      = 'http://127.0.0.1:8769/'
$Servidor = Join-Path $PSScriptRoot 'servidor.py'

function Test-Servidor {
    try { Invoke-RestMethod -Uri "${Url}estado" -TimeoutSec 15 } catch { $null }
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
    if (-not $ok) { throw 'El servidor de insiders no arranco' }
}

Start-Process $Url
Write-Output "Tablero de insiders abierto en $Url"
