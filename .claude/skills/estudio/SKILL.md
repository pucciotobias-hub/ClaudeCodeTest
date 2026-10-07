---
name: estudio
description: Corre ahora un estudio de GGAL (apertura, mediodia, cierre, auditoria o semanal) con el mismo lanzador que usan las tareas programadas, y resume el informe. Usar cuando el usuario pide "/estudio", "corré el estudio", "haceme la apertura/el mediodía/el cierre ahora".
---

# Estudio de GGAL a pedido

Corre `scripts/ggal_estudio.ps1` a mano. El lanzador ya hace todo lo delicado
(candado del gráfico, Chrome con CDP, commit, aviso por Telegram): acá solo se
elige el turno, se verifica que se pueda correr y se informa el resultado.
No manejes el gráfico de TradingView desde esta sesión en ningún paso.

## 1. Elegir el turno

Si el usuario lo nombró (`/estudio cierre`), es ese. Si no, por la hora de Argentina:

| Hora | Turno |
|---|---|
| 10:30 a 12:59 | `apertura` |
| 13:00 a 16:59 | `mediodia` |
| 17:00 en adelante | `cierre` |

Antes de las 10:30, o en sábado, domingo o feriado de EE. UU., el mercado está
cerrado: decilo y preguntá qué turno quiere en vez de elegir uno.
`auditoria` y `semanal` solo si los pide por nombre.

## 2. Verificar antes de lanzar

1. **Que no haya otra corrida.** Leé el final de `logs/ggal_estudio.log`. Si la
   última línea `=== INICIO` no tiene después su `=== FIN` ni un `ERROR`/`WARN`
   de salida, y es de los últimos 45 minutos, hay un estudio en curso: avisá y
   no lances nada.
2. **Que no pise un informe de hoy.** La salida es
   `estudios/ggal/<fecha>-<turno>.md` (`auditorias/<fecha>.md`,
   `semanal/<fecha>.json`). Si ya existe y está commiteado
   (`git ls-files -- <ruta>`), correrlo de nuevo lo reescribe. Preguntá antes
   de seguir, salvo que el usuario ya haya dicho que quiere rehacerlo.

## 3. Lanzar

En segundo plano, porque tarda entre 5 y 10 minutos:

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ggal_estudio.ps1 -Turno <turno> -Forzar
```

`-Forzar` va siempre: sin él, el lanzador se saltea la corrida fuera de la
ventana horaria del turno o si el informe ya está commiteado. Decile al usuario
que arrancó y qué turno es; no te quedes consultando el log en bucle.

## 4. Informar

Cuando el proceso termina:

- **Salió bien** (el log cierra con `=== FIN` y el informe existe): leé el
  informe y resumí en pocas líneas el precio, qué cambió desde el informe
  anterior y qué decide la rueda. Dá la ruta del archivo.
- **Se salteó** (`Hay otro estudio GGAL corriendo`): decilo, no reintentes.
- **Falló** (`Claude salio con codigo N` o no apareció el informe): mostrá las
  últimas líneas del log que explican por qué. No lo vuelvas a lanzar por tu
  cuenta.

El lanzador commitea y pushea el informe y manda el aviso de Telegram; no hagas
ninguna de las dos cosas a mano.
