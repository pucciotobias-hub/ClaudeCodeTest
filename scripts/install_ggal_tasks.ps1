<#
.SYNOPSIS
    Registra (o borra) las Tareas Programadas del estudio diario de GGAL.

.DESCRIPTION
    Crea tres tareas, hora local (ART, UTC-3):

      EstudioGGAL-Apertura   L-V 10:20, 10:50        -> antes de que abra NY
      EstudioGGAL-Cierre     L-V 17:15, 17:50, 18:30 -> despues del cierre
      AuditoriaGGAL          V   19:30, 20:30        -> despues del ultimo
                                                        reintento del cierre

    El primer disparo es el bueno; los otros son reintentos. Si el primero murio
    en el despertar de la maquina (0xC000013A, paso el 11 y el 23-sep), el
    siguiente lo cubre. Si el informe ya existe, el wrapper sale sin hacer nada.

    Todas corren SOLO con el usuario logueado: Chrome necesita una sesion de
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

$LaV = @('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')
$Tareas = @(
    @{ Nombre = 'EstudioGGAL-Apertura'; Turno = 'apertura';  Horas = @('10:20', '10:50');          Dias = $LaV;       Desc = 'Estudio tecnico GGAL ADR - pre-apertura de NY' }
    @{ Nombre = 'EstudioGGAL-Cierre';   Turno = 'cierre';    Horas = @('17:15', '17:50', '18:30'); Dias = $LaV;       Desc = 'Estudio tecnico GGAL ADR - post-cierre de NY' }
    @{ Nombre = 'ReporteSemanalGGAL';   Turno = 'semanal';   Horas = @('09:30', '12:00');          Dias = @('Monday'); Desc = 'Reporte semanal GGAL: noticias macro y panorama, publicado en claude.ai' }
    @{ Nombre = 'AuditoriaGGAL';        Turno = 'auditoria'; Horas = @('19:30', '20:30');          Dias = @('Friday'); Desc = 'Auditoria semanal de los estudios GGAL contra el precio' }
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

            $trigger = @($t.Horas | ForEach-Object {
                New-ScheduledTaskTrigger -Weekly -DaysOfWeek $t.Dias -At $_
            })

            # Interactive: la tarea corre en la sesion del usuario logueado, que es
            # lo que Chrome necesita para renderizar. Sin esto el chart no repinta.
            $principal = New-ScheduledTaskPrincipal `
                -UserId "$env:USERDOMAIN\$env:USERNAME" `
                -LogonType Interactive `
                -RunLevel Limited

            # Limite de 45 min: 20 quedaba corto. La corrida del cierre del 2026-09-09
            # la mato el scheduler en el limite (0x41306 SCHED_S_TASK_TERMINATED) y la
            # del 2026-09-10 tardo 11m37s. Con los reintentos por caida del CDP una
            # corrida normal puede pasar los 20.
            # (El comentario va aca arriba y no entre los parametros: una linea de
            # comentario en medio de una continuacion con backtick corta el comando.)
            $settings = New-ScheduledTaskSettingsSet `
                -StartWhenAvailable `
                -DontStopIfGoingOnBatteries `
                -AllowStartIfOnBatteries `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
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

            Write-Output "Registrada: $($t.Nombre) -> $($t.Dias -join ',') $($t.Horas -join ', ') ART"
        }

        Write-Output ""
        Write-Output "Listo. Verificar con: .\install_ggal_tasks.ps1 -Accion estado"
        Write-Output "Correr a mano:        .\ggal_estudio.ps1 -Turno apertura"
    }
}
