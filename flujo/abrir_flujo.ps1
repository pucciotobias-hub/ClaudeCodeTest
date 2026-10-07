<#
.SYNOPSIS
    Abre el tablero de flujo del ADR de GGAL en el navegador.

.DESCRIPTION
    Levanta flujo/servidor.py en segundo plano si no esta corriendo (baja las
    velas de 5 minutos de yfinance cuando la pagina las pide, a lo sumo una vez
    por minuto) y abre http://127.0.0.1:8767/ en el navegador por defecto.

.EXAMPLE
    .\flujo\abrir_flujo.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Url      = 'http://127.0.0.1:8767/'
$Servidor = Join-Path $PSScriptRoot 'servidor.py'

function Test-Servidor {
    try { Invoke-RestMethod -Uri "${Url}datos" -TimeoutSec 15 } catch { $null }
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
    if (-not $ok) { throw 'El servidor de flujo no arranco' }
}

Start-Process $Url
Write-Output "Tablero de flujo abierto en $Url"
