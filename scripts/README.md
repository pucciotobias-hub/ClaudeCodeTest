# Estudio diario de GGAL ADR — automatizacion

Corre el estudio tecnico de siempre sobre el ADR de GGAL (NASDAQ) en TradingView,
dos veces por dia habil, y deja el informe versionado en `estudios/ggal/`.

## Piezas

| Archivo | Que hace |
|---|---|
| `ggal_estudio_prompt.md` | **La receta.** Que niveles trazar, como leer el macro, el fix de paneles de TradingView, y el formato del informe. Es lo unico que hay que editar para cambiar el estudio. |
| `ggal_estudio.ps1` | Wrapper: levanta Chrome con CDP si esta caido y dispara `claude -p` con la receta. |
| `relanzar_chrome_cdp.ps1` | Levanta Chrome con CDP en el 9222 (idempotente). Lo llama el wrapper en el preflight, y tambien Claude si el CDP se cae a mitad del estudio. |
| `install_ggal_tasks.ps1` | Registra/borra las dos Tareas Programadas de Windows. |

## Horarios (ART, UTC-3)

| Tarea | Cuando | Por que |
|---|---|---|
| `EstudioGGAL-Apertura` | L-V 10:20 | 10 min antes de que abra NY (10:30 ART). Llegas con el mapa armado. |
| `EstudioGGAL-Cierre` | L-V 17:15 | 15 min despues del cierre (17:00 ART). Vela diaria ya cerrada. |

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
```

## Salida

- Informe: `estudios/ggal/YYYY-MM-DD-<turno>.md`, commiteado y pusheado solo.
- Screenshot del chart: `C:\Users\Tobias\Desktop\tradingview-mcp-jackson\screenshots\`
- Log de las corridas: `logs/ggal_estudio.log` (gitignoreado).

## Requisitos y limitaciones

- **Sesion de escritorio activa.** Las tareas corren con `LogonType Interactive`
  porque Chrome necesita renderizar de verdad. Si la maquina esta apagada o con
  la sesion cerrada, la corrida se saltea (`-StartWhenAvailable` la dispara
  cuando volves, aunque con datos ya viejos).
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
