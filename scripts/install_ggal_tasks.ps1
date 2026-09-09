<#
.SYNOPSIS
    Registra (o borra) las Tareas Programadas del estudio diario de GGAL.

.DESCRIPTION
    Crea dos tareas de lunes a viernes, hora local (ART, UTC-3):

      EstudioGGAL-Apertura   10:20  -> 10 min antes de que abra NY
      EstudioGGAL-Cierre     17:15  -> 15 min despues del cierre

    Ambas corren SOLO con el usuario logueado: Chrome necesita una sesion de
    escritorio activa para renderizar el chart.

.PARAMETER Accion
    'instalar' (default), 'desinstalar' o 'estado'.

.EXAMPLE
    .\install_ggal_tasks.ps1
    .\install_ggal_tasks.ps1 -Accion estado
    .\install_ggal_tasks.ps1 -Accion desinstalar
#>
[CmdletBinding()]
param(
    [ValidateSet('instalar', 'desinstalar', 'estado')]
    [string]$Accion = 'instalar'
)

$ErrorActionPreference = 'Stop'

$Runner = Join-Path $PSScriptRoot 'ggal_estudio.ps1'
$WorkDir = Split-Path -Parent $PSScriptRoot

$Tareas = @(
    @{ Nombre = 'EstudioGGAL-Apertura'; Turno = 'apertura'; Hora = '10:20'; Desc = 'Estudio tecnico GGAL ADR - pre-apertura de NY' }
    @{ Nombre = 'EstudioGGAL-Cierre';   Turno = 'cierre';   Hora = '17:15'; Desc = 'Estudio tecnico GGAL ADR - post-cierre de NY' }
)

switch ($Accion) {

    'estado' {
        foreach ($t in $Tareas) {
            $task = Get-ScheduledTask -TaskName $t.Nombre -ErrorAction SilentlyContinue
            if ($task) {
                $info = Get-ScheduledTaskInfo -TaskName $t.Nombre
                Write-Output "$($t.Nombre): $($task.State) | ultima=$($info.LastRunTime) rc=$($info.LastTaskResult) | proxima=$($info.NextRunTime)"
            } else {
                Write-Output "$($t.Nombre): NO REGISTRADA"
            }
        }
    }

    'desinstalar' {
        foreach ($t in $Tareas) {
            if (Get-ScheduledTask -TaskName $t.Nombre -ErrorAction SilentlyContinue) {
                Unregister-ScheduledTask -TaskName $t.Nombre -Confirm:$false
                Write-Output "Borrada: $($t.Nombre)"
            } else {
                Write-Output "No existia: $($t.Nombre)"
            }
        }
    }

    'instalar' {
        if (-not (Test-Path $Runner)) { throw "No se encontro $Runner" }

        foreach ($t in $Tareas) {
            $action = New-ScheduledTaskAction `
                -Execute 'powershell.exe' `
                -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Runner`" -Turno $($t.Turno)" `
                -WorkingDirectory $WorkDir

            $trigger = New-ScheduledTaskTrigger -Weekly `
                -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
                -At $t.Hora

            # Interactive: la tarea corre en la sesion del usuario logueado, que es
            # lo que Chrome necesita para renderizar. Sin esto el chart no repinta.
            $principal = New-ScheduledTaskPrincipal `
                -UserId "$env:USERDOMAIN\$env:USERNAME" `
                -LogonType Interactive `
                -RunLevel Limited

            $settings = New-ScheduledTaskSettingsSet `
                -StartWhenAvailable `
                -DontStopIfGoingOnBatteries `
                -AllowStartIfOnBatteries `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
                -MultipleInstances IgnoreNew

            if (Get-ScheduledTask -TaskName $t.Nombre -ErrorAction SilentlyContinue) {
                Unregister-ScheduledTask -TaskName $t.Nombre -Confirm:$false
            }

            Register-ScheduledTask `
                -TaskName $t.Nombre `
                -Action $action `
                -Trigger $trigger `
                -Principal $principal `
                -Settings $settings `
                -Description $t.Desc | Out-Null

            Write-Output "Registrada: $($t.Nombre) -> L-V $($t.Hora) ART"
        }

        Write-Output ""
        Write-Output "Listo. Verificar con: .\install_ggal_tasks.ps1 -Accion estado"
        Write-Output "Correr a mano:        .\ggal_estudio.ps1 -Turno apertura"
    }
}
