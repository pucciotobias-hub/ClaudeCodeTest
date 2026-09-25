# Estudio diario de GGAL ADR — automatizacion

Corre el estudio tecnico de siempre sobre el ADR de GGAL (NASDAQ) en TradingView,
dos veces por dia habil, y deja el informe versionado en `estudios/ggal/`.

## Piezas

| Archivo | Que hace |
|---|---|
| `ggal_estudio_prompt.md` | **La receta.** Que niveles trazar, como leer el macro, el fix de paneles de TradingView, y el formato del informe. Es lo unico que hay que editar para cambiar el estudio. |
| `ggal_estudio.ps1` | Wrapper: levanta Chrome con CDP si esta caido y dispara `claude -p` con la receta. |
| `relanzar_chrome_cdp.ps1` | Levanta Chrome con CDP en el 9222 (idempotente). Lo llama el wrapper en el preflight, y tambien Claude si el CDP se cae a mitad del estudio. |
| `install_ggal_tasks.ps1` | Registra/borra las tres Tareas Programadas de Windows. |
| `ggal_auditoria_prompt.md` | Receta de la **auditoria semanal**: contrasta los estudios contra lo que hizo el precio y propone cambios a la receta del estudio. |
| `ggal_semanal_prompt.md` | Receta del **reporte semanal**: numeros de la semana del feed, noticias macro de la web (con fuente) y panorama de la semana que viene. |
| `ggal_semanal_template.html` | Plantilla fija de la pagina semanal. El agente solo reemplaza el bloque JSON de datos; el diseño no cambia. |
| `ggal_semanal_url.txt` | Link fijo de la pagina publicada en claude.ai (lo crea la primera corrida). |
| `ggal_auditoria.py` | La parte objetiva de la auditoria (niveles respetados/perforados/rotos, extremos anticipados contra una grilla, encabezados contra la barra). Se puede correr a mano: `python scripts/ggal_auditoria.py --barras scripts/ggal_bars.json`. |

## Horarios (ART, UTC-3)

| Tarea | Cuando | Por que |
|---|---|---|
| `EstudioGGAL-Apertura` | L-V 10:20 (reintento 10:50) | 10 min antes de que abra NY (10:30 ART). Llegas con el mapa armado. |
| `EstudioGGAL-Cierre` | L-V 17:15 (reintentos 17:50 y 18:30) | 15 min despues del cierre (17:00 ART). Vela diaria ya cerrada. |
| `ReporteSemanalGGAL` | L 09:30 (reintento 12:00) | Semana cerrada, antes de la apertura. El de 12:00 va despues de la apertura para no pisarse en el chart. |
| `AuditoriaGGAL` | V 19:30 (reintento 20:30) | Despues del ultimo reintento del cierre del viernes. |

Los reintentos no duplican nada: si el informe del dia ya existe, el wrapper sale
sin hacer nada. Tampoco corre fuera de su ventana (apertura 10:00-16:30, cierre
17:00-23:59), para no escribir un cierre con fecha del dia siguiente ni pisarse
con la apertura.

## Instalacion

```powershell
cd C:\Users\Tobias\Desktop\ClaudeCodeTest\scripts
.\install_ggal_tasks.ps1
```

Verificar / borrar:

```powershell
.\install_ggal_tasks.ps1 -Accion estado
.\install_ggal_tasks.ps1 -Accion desinstalar
```

## Correrlo a mano

```powershell
.\ggal_estudio.ps1 -Turno apertura
.\ggal_estudio.ps1 -Turno cierre
.\ggal_estudio.ps1 -Turno auditoria
.\ggal_estudio.ps1 -Turno cierre -Forzar   # fuera de ventana o pisando el informe de hoy
```

## Salida

- Informe: `estudios/ggal/YYYY-MM-DD-<turno>.md`, commiteado y pusheado solo.
- Reporte semanal: `estudios/ggal/semanal/YYYY-MM-DD.html`, publicado siempre en el mismo
  link de claude.ai (el de `scripts/ggal_semanal_url.txt`).
- Auditoria: `estudios/ggal/auditorias/YYYY-MM-DD.md`. **Las propuestas de cambio a
  la receta no se aplican solas**: las lee Tobias y decide. Una receta que se
  reescribe sola sin que nadie la mire puede derivar sin que se note.
- Screenshot del chart: `C:\Users\Tobias\Desktop\tradingview-mcp-jackson\screenshots\`
- Log de las corridas: `logs/ggal_estudio.log` (gitignoreado).

## Requisitos y limitaciones

- **Sesion de escritorio activa.** Las tareas corren con `LogonType Interactive`
  porque Chrome necesita renderizar de verdad. Si la maquina esta apagada o con
  la sesion cerrada, la corrida se saltea (`-StartWhenAvailable` la dispara
  cuando volves, aunque con datos ya viejos).
- **Suspension: la causa numero uno de corridas muertas.** Documentado con los
  eventos de Kernel-Power del 9 al 11 de septiembre de 2026. Son dos fallas
  distintas:
  1. *La maquina duerme a la hora del trigger.* La tarea no corre; se pone al dia
     en el instante del despertar. Si ese despertar es manual, el proceso arranca
     en plena transicion y muere antes de escribir la primera linea del log
     (11-sep 10:22:41, "motivo: Power Button", exit `0xC000013A`). Si el
     despertar llega horas despues, el informe sale viejo: el cierre del 10-sep
     corrio a las 00:55 del 11-sep.
  2. *La maquina se duerme a mitad de la corrida.* El estudio tarda ~12 min y
     nadie toca el teclado, asi que el Idle Timeout se cumple siempre
     (10-sep 10:27:28, exit `0xC000013A`). **Esto lo arregla el wrapper**, que
     ahora sostiene `SetThreadExecutionState` con `ES_SYSTEM_REQUIRED |
     ES_DISPLAY_REQUIRED` mientras dura el estudio y lo suelta al terminar. La
     pantalla queda prendida esas ~12 min, a proposito: Chrome tiene que renderizar.

  3. *La maquina se suspende a mitad por otra via* (tapa, boton, "Application
     API"): `ES_SYSTEM_REQUIRED` solo frena el Idle Timeout. El 17-sep se
     suspendio a las 19:31 con claude corriendo y desperto el 22-sep: la corrida
     quedo 4 dias "en ejecucion", el Programador ignoro todos los disparos
     (`IgnoreNew`) y se perdieron 4 informes. **Arreglado**: el wrapper corta a
     claude a los 40 min de reloj de pared, asi que al despertar lo mata y libera
     la tarea para el disparo siguiente.

  La falla 1 **no esta arreglada del todo, por decision del usuario**: `WakeToRun`
  haria que la laptop se despierte sola, y no se quiere eso. Lo que si hay son
  reintentos: si el primer disparo muere en el despertar, el siguiente lo cubre.
  Si la maquina duerme durante toda la ventana, el informe no sale; para esos
  dias, correrlo a mano con `-Forzar`.
- **El limite de ejecucion es de 45 min.** Eran 20 y el scheduler mato la corrida
  del cierre del 9-sep al llegar al limite (`0x41306`). Una corrida normal tarda
  entre 7 y 12 min.
- **Chrome + CDP en el puerto 9222.** Lo levanta `relanzar_chrome_cdp.ps1` con
  `Start-Process` sobre el perfil `~\tv-cdp-profile`. Ojo: `tv_launch` del MCP y
  `launch-tv.bat` **no funcionan** en esta maquina (es TradingView web, no la app
  de escritorio). Si ya hay un Chrome del perfil CDP colgado sin bindear el
  puerto, el script lo mata primero — filtrado por ruta del perfil, asi que el
  Chrome normal del usuario no se toca.
- **El CDP se cae solo a mitad de una corrida** (tipico: un `chart_set_symbol` del
  macro devuelve `WebSocket connection closed`). Por eso `ggal_estudio.ps1` le
  pre-aprueba a Claude el patron `Bash(powershell*relanzar_chrome_cdp.ps1*)`: sin
  ese permiso el relanzamiento queda bloqueado y el informe sale parcial (pasó en
  la primera corrida del 2026-09-09). Despues de un relanzamiento hay que
  re-verificar dibujos e indicadores: el layout recarga del estado guardado y se
  pueden perder los agregados por MCP.
- **Feriados de NYSE.** Las tareas corren igual L-V; en un feriado el informe va
  a salir con la vela vacia y lo marca arriba de todo. No hay calendario de
  feriados cableado.
- **No es asesoramiento financiero.** El informe describe el cuadro tecnico y
  escenarios; no emite ordenes.
