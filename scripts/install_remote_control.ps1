<#
.SYNOPSIS
    Registra (o borra) la tarea programada que levanta Remote Control al iniciar sesion.

.DESCRIPTION
    RemoteControlClaude: al iniciar sesion el usuario, corre scripts\remote_control.ps1,
    que deja la sesion 'ggal' disponible en la app de Claude del celular. Corre solo
    con el usuario logueado (igual que los estudios: TradingView necesita escritorio)
    y sin limite de tiempo. Si la notebook se suspende, la sesion no responde hasta
    que despierte.

.PARAMETER Accion
    'instalar' (default), 'desinstalar' o 'estado'.

.EXAMPLE
    .\scripts\install_remote_control.ps1
    .\scripts\install_remote_control.ps1 -Accion estado
#>
[CmdletBinding()]
param(
    [ValidateSet('instalar', 'desinstalar', 'estado')]
    [string]$Accion = 'instalar'
)

$ErrorActionPreference = 'Stop'
$Nombre = 'RemoteControlClaude'
$Script = Join-Path $PSScriptRoot 'remote_control.ps1'

switch ($Accion) {
    'estado' {
        $t = Get-ScheduledTask -TaskName $Nombre -ErrorAction SilentlyContinue
        if ($t) {
            $i = Get-ScheduledTaskInfo -TaskName $Nombre
            Write-Output "${Nombre}: $($t.State) | ultima=$($i.LastRunTime) rc=$($i.LastTaskResult)"
        } else {
            Write-Output "${Nombre}: NO REGISTRADA"
        }
    }
    'desinstalar' {
        if (Get-ScheduledTask -TaskName $Nombre -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $Nombre -Confirm:$false
            Write-Output "Borrada: $Nombre"
        } else {
            Write-Output "No existia: $Nombre"
        }
    }
    'instalar' {
        if (-not (Test-Path $Script)) { throw "No se encontro $Script" }
        # Minimizada y no oculta: si Claude Code pregunta algo, la ventana queda a mano.
        $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$Script`"" `
            -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
        # Sin limite de tiempo (00:00:00): el proceso tiene que quedar vivo todo el dia.
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
        if (Get-ScheduledTask -TaskName $Nombre -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $Nombre -Confirm:$false
        }
        Register-ScheduledTask -TaskName $Nombre -Action $action -Trigger $trigger -Principal $principal `
            -Settings $settings -Description 'Remote Control de Claude Code en el repo (sesion ggal para el celular)' | Out-Null
        Write-Output "Registrada: $Nombre -> al iniciar sesion"
        Write-Output "Arrancar ahora sin reiniciar: Start-ScheduledTask -TaskName $Nombre"
    }
}
