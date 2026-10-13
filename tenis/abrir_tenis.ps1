<#
.SYNOPSIS
    Abre el juego de tenis en el navegador.

.DESCRIPTION
    Levanta tenis/servidor.py en segundo plano si no esta corriendo y abre
    http://127.0.0.1:8768/ en el navegador por defecto.

.EXAMPLE
    .\tenis\abrir_tenis.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Url      = 'http://127.0.0.1:8768/'
$Servidor = Join-Path $PSScriptRoot 'servidor.py'

function Test-Servidor {
    try { Invoke-RestMethod -Uri "${Url}vivo" -TimeoutSec 2 } catch { $null }
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
    if (-not $r) { throw 'El servidor de tenis no arranco' }
}

Start-Process $Url
Write-Output "Tenis abierto en $Url"
