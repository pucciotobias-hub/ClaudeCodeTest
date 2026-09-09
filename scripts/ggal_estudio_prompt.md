# Estudio diario de GGAL ADR — receta

Sos el analista que corre el estudio tecnico de siempre sobre el ADR de GGAL en
TradingView. Este prompt lo dispara una Tarea Programada de Windows, asi que
**no hay nadie mirando**: no preguntes nada, resolve con los defaults y dejá el
informe escrito y commiteado.

El wrapper ya se encargo de levantar Chrome con CDP en el puerto 9222 y te pasa,
arriba de este texto, la fecha y el turno (`apertura` o `cierre`).

---

## 1. Verificar el chart

- `tv_health_check`. Si falla, corré el relanzamiento del punto 1.bis y reintentá.
  Si despues de dos intentos sigue sin responder, escribí el informe igual marcando
  **"SIN DATOS: TradingView no respondio"** y terminá.
- El chart guardado es `pzxwEAwm`.
- `chart_set_symbol` → `NASDAQ:GGAL`, `chart_set_timeframe` → `D`.

## 1.bis Si el CDP se cae a mitad (pasa seguido)

En cualquier momento una herramienta puede devolver `WebSocket connection closed`
o `CDP connection failed`. Tipicamente en un `chart_set_symbol` del macro.
**No abandones el paso ni escribas N/D todavia**: recuperá el chart.

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/relanzar_chrome_cdp.ps1
```

Ese comando esta pre-aprobado, corre desatendido y tarda ~25s. Es idempotente:
si el CDP ya esta bien no toca nada. Despues:

1. `tv_health_check` para confirmar.
2. **Ojo:** al reiniciar Chrome el layout recarga del estado guardado y se pueden
   perder dibujos e indicadores agregados por MCP. Verificá con `draw_list` y
   `chart_get_state`, y reaplicá el punto 2 y el 3 si hace falta.
3. Retomá donde estabas.

Si falla dos veces seguidas, ahi si seguí con lo que tengas y marcá lo que falta
como N/D, dejando la nota de corrida al final del informe.

## 2. Arreglar paneles si hace falta

Bug conocido: despues de un rato la pagina deja de repintar y los paneles de
indicadores quedan con altura 0 (el RSI existe pero es invisible), y
`capture_screenshot` devuelve un frame viejo. `setHeight` / `setAllPanesHeight` /
`restore()` no sirven. El unico arreglo es forzar un relayout con `ui_evaluate`:

```js
const w = window.TradingViewApi.activeChart()._chartWidget;
w.resize(1279,584); w.resize(1280,585);
```

Notas:
- `paneWidgets().map(p=>p.height())` va **una llamada atrasado**: consultalo en un
  `ui_evaluate` aparte.
- Paneles fantasma (stretchFactor 0, sin fuentes): `w.model().model().removePane(pane)`.
- Volume como overlay del panel de precio: `chart.createStudy('Volume', true, false)`
  (el `true` es forceOverlay). `chart_manage_indicator add` lo mete en panel aparte.

## 3. Indicadores

Tienen que quedar **visibles** y reportando valor en `data_get_study_values`:
- **EMA 20** (Moving Average Exponential, length 20, source close)
- **RSI 14** (Relative Strength Index)
- **Volume** como overlay

Si `data_get_study_values` no los devuelve, aplicá el fix del punto 2 y reintentá.

## 4. Datos

- `data_get_ohlcv` count=60 en diario. Con eso calculás todo; no busques precios en la web.
- Calculá vos EMA20 y RSI14 (Wilder) sobre los cierres para cruzar contra lo que
  reporta el chart. Si difieren mas de 1%, confiá en el chart y anotalo.
  Si escribís un script auxiliar o volcás las barras a un archivo, **borralo al
  terminar**: el repo solo tiene que quedar con el informe.
- **Macro**: leelo del feed en vivo, NUNCA de la web. `quote_get` ignora el simbolo
  y devuelve el del chart, asi que para cada ticker hay que `chart_set_symbol`,
  leer, y seguir. Tickers: `BATS:SPY`, `AMEX:EWZ`, y si estan a mano `TVC:DXY` y
  `BATS:ARGT`. Para el % del dia: timeframe `D`, `data_get_ohlcv` count=3 y
  calcular (cierre hoy − cierre previo) / cierre previo.
- Al terminar el macro, **volvé a `NASDAQ:GGAL` en diario**.

## 5. Redibujar los niveles

- `draw_list` para ver que hay, despues `draw_clear`, despues redibujar todo.
- Los niveles salen de los maximos y minimos de swing de las ultimas ~30 ruedas
  mas el mapa vigente que esta en el informe anterior. Maximo **10 lineas
  horizontales**: si un nivel ya no marca nada, sacalo y decilo en el informe.
- Colores: resistencias `#ef5350`, soporte `#26a69a`, pivote `#ffb300` (linewidth 3).
  Etiquetá cada linea con `showLabel:true` y un `text` corto (ej. `S1 43.50 piso triple`).
- **Zona critica** alrededor del pivote: un `rectangle` azul (`#2962ff`, fondo transparente).
- **Directriz bajista** desde el maximo de 58.14 (18-jun-2026) hasta 40.63 (21-sep):
  `trend_line` gris punteada. OJO: TradingView la plotea en espacio de **barras**,
  no de tiempo lineal — para saber por donde pasa hoy, interpolá por indice de
  barra, no por dias calendario (interpolar por calendario da ~0.35 de mas).
- Dejá el chart con un rango visible de las ultimas ~40 ruedas y sacá un
  `capture_screenshot` con nombre `ggal_TURNO_FECHA`.

## 6. Escribir el informe

Archivo: `estudios/ggal/<FECHA>-<TURNO>.md` (ej. `estudios/ggal/2026-09-09-apertura.md`).

**Antes de escribir, leé el informe mas reciente que ya exista en `estudios/ggal/`**
y marcá explicitamente que cambio desde entonces. Ese diff es la parte mas util
del informe: si no cambio nada, decilo en una linea y no inventes movimiento.

Estructura:

```markdown
# GGAL ADR — <FECHA> (<TURNO>)

**Precio** X · **Dia** O/H/L/C · **EMA20** X · **RSI14** X

## Que cambio desde el informe anterior
...

## Estructura
(tendencia, maximos/minimos de swing, que se rompio o se respeto)

## Mapa de niveles
| | Nivel | Que es |
(tabla con R4..R1, PIVOTE, S1..S5)

## Indicadores
(EMA20 vs precio, RSI y si hay divergencia, volumen relativo)

## Macro del feed
(SPY, EWZ, DXY, ARGT con % del dia — y si GGAL se mueve con el bloque o solo)

## Escenarios
(rotura / recuperacion / rango, con los niveles que gatillan cada uno)
```

Reglas de escritura:
- Español rioplatense, directo, sin relleno. Nada de "es importante notar que".
- Numeros concretos siempre. Si un dato no lo pudiste leer, escribí `N/D`, nunca
  un numero inventado ni un cero enganioso.
- **No es asesoramiento financiero**: describí el cuadro tecnico y los escenarios,
  no des ordenes de compra/venta con tamanio de posicion.
- Si el mercado esta cerrado o la vela del dia esta vacia, decilo arriba de todo.

## 7. Actualizar memoria y commitear

- Si el mapa de niveles cambio, actualizá
  `C:\Users\Tobias\.claude\projects\C--Users-Tobias-Desktop-ClaudeCodeTest\memory\project_ggal_adr_levels.md`
  y la linea correspondiente de `MEMORY.md`.
- `git add estudios/ggal/<archivo>` (solo eso — nunca `git add -A`),
  commit `estudio GGAL <FECHA> <TURNO>`, y `git push origin master`.
- Si el push falla, no reintentes en loop: dejá el commit local y anotá el error
  al final del informe.
