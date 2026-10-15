<#
.SYNOPSIS
    Deja levantada una sesion de Remote Control de Claude Code en el repo, para
    manejarla desde la app de Claude en el celular (pestana Code) o claude.ai/code.

.DESCRIPTION
    Lo lanza la tarea programada RemoteControlClaude al iniciar sesion en Windows
    (instalar con .\scripts\install_remote_control.ps1). Pedido y aprobado por el
    usuario el 15-oct-2026: la notebook queda manejable desde su cuenta de Claude
    mientras este prendida y despierta. Si el proceso se cae, lo vuelve a levantar
    a los 30 segundos. Deja un renglon por arranque y salida en
    logs\remote_control.log.

    La primera vez Claude Code pregunta "Enable Remote Control? (y/n)": hay que
    contestarla a mano una vez corriendo `claude remote-control` en una terminal.
    Sin eso, cada arranque se queda esperando la respuesta.

.EXAMPLE
    .\scripts\remote_control.ps1
#>
[CmdletBinding()]
param(
    [string]$Nombre = 'ggal'
)

$ErrorActionPreference = 'Continue'
$Repo   = Split-Path -Parent $PSScriptRoot
$Claude = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
$LogDir = Join-Path $Repo 'logs'
$Log    = Join-Path $LogDir 'remote_control.log'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log([string]$texto) {
    Add-Content -Path $Log -Encoding utf8 -Value ("{0} | {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $texto)
}

Set-Location $Repo
while ($true) {
    Write-Log "INICIO remote-control (sesion '$Nombre')"
    & $Claude remote-control --name $Nombre --permission-mode auto
    Write-Log "FIN remote-control (codigo $LASTEXITCODE); reintento en 30 s"
    Start-Sleep -Seconds 30
}
