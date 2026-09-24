# Estudio diario de GGAL ADR — receta

Sos el analista que corre el estudio tecnico de siempre sobre el ADR de GGAL en
TradingView. Este prompt lo dispara una Tarea Programada de Windows, asi que
**no hay nadie mirando**: no preguntes nada, resolve con los defaults y dejá el
informe escrito y commiteado.

El wrapper ya se encargo de levantar Chrome con CDP en el puerto 9222 y te pasa,
arriba de este texto, la fecha y el turno (`apertura` o `cierre`).

**Nunca esperes.** Corres en modo headless (`claude -p`): cuando terminas tu turno
se termina la corrida, no hay forma de "seguir despues". Si cortas el turno para
que la vela junte mas operaciones, el proceso sale con codigo 0 **sin informe** y
la corrida del dia se pierde. Paso el 2026-09-11 en la apertura: el unico output
fue "Esperando ~2,5 min a que la vela del dia junte mas operaciones antes de la
lectura final" y no quedo nada escrito.

Entonces: **lee lo que hay cuando lo lees y segui.** En la apertura la vela va a
tener pocos minutos y poco volumen — eso no es un problema a resolver esperando,
es un dato: deci la edad de la vela y marca el volumen relativo como `N/D`. Lo
mismo con cualquier otra tentacion de pausar. El informe escrito con datos de
hace 3 minutos vale; el informe que no existe, no.

---

## 1. Verificar el chart

- `tv_health_check`. Si falla, corré el relanzamiento del punto 1.bis y reintentá.
  Si despues de dos intentos sigue sin responder, escribí el informe igual marcando
  **"SIN DATOS: TradingView no respondio"** y terminá.
- El chart guardado es `pzxwEAwm`.
- `chart_set_timeframe` → `D` **y despues** `chart_set_symbol` → `NASDAQ:GGAL`
  (en ese orden: al reves el feed se queda pegado en el simbolo anterior; paso en
  7 de las primeras 12 corridas). Verificá en un `ui_evaluate` aparte que
  `activeChart().symbol()` sea `BATS:GGAL`, que `resolution()` sea `1D` y que la
  ultima barra sea de la ultima rueda. Si no: `location.reload()`,
  `tv_health_check` y repetí. Lo mismo en cada ticker del macro.

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
`restore()` no sirven. El primer arreglo es forzar un relayout con `ui_evaluate`:

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
- **Si el doble resize no alcanza** (no alcanzo en 4 de las primeras 12 corridas):
  `location.reload()` pelado. Si despues del reload un panel sigue en altura 0,
  `paneWidget.setSize({width, height})` sobre cada panel.

## 3. Indicadores

Tienen que quedar **visibles** y reportando valor **leido del modelo**
(`dataSources()` de la serie → `data().last()`), sobre el simbolo verificado.
**No uses `data_get_study_values`**: hace derivar el simbolo solo y se lleva los
dibujos (paso el 2026-09-22, se perdieron los 12).
- **EMA 20** (Moving Average Exponential, length 20, source close)
- **RSI 14** (Relative Strength Index)
- **Volume** como overlay

El chart tiene ademas la estrategia **GGAL Señales** (Pine, señales intradia en
15m, con su Strategy Tester). **No la saques ni la toques.** Sus plots (EMA
rapida, EMA lenta, VWAP) y su tabla no son parte del estudio: la EMA20 es la
del indicador "Moving Average Exponential". En diario no marca nada. Al terminar
no hace falta volver el chart a 15m: lo hace el vigia de señales.

Si el modelo no devuelve valores (estudio mudo, series en 0), aplicá el fix del
punto 2 y reintentá.

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
  mas el mapa vigente del informe anterior. Maximo **10 lineas horizontales**,
  repartidas asi:
  - **Por lo menos 3 de cada lado del precio**, dentro de ~5% (un rango de 3
    ruedas de GGAL).
  - **A mas de 5% del precio, una sola linea por lado** (el gatillo de fondo). El
    resto sale del mapa aunque tenga historia; si el precio vuelve, se redibuja.
    Decí en el informe que salio.
  - Si del lado hacia donde va la tendencia no hay swings de 30 ruedas, buscá mas
    atras (meses o el año anterior) antes de dejar ese lado con menos de 3 lineas.
  - (Auditoria 2026-09-24: el 55% de las lineas no se toco en 3 ruedas, casi todas
    resistencias viejas, y del lado de la caida quedaban dos soportes.)
- **R o S se decide por la posicion contra el ultimo precio, no por la historia del
  nivel.** Un "ex soporte" que quedo debajo del precio es S. La historia va en la
  columna "Que es".
- **Los niveles son bandas, no lineas.** Los que aguantaron se perforaron en el
  intradia una mediana de 0,8% antes de recuperar. En el texto, un nivel "se
  perdio" cuando se perdio en cierre; una perforacion intradia se describe como tal.
- **Colores, siempre con opacidad baja.** Las lineas son referencia, no protagonistas:
  a full color tapan las velas y molestan para leer el precio. Pasá el alfa dentro
  del color, en `rgba(...)`, que es lo que acepta `linecolor` en los `overrides`:

  | Que | `linecolor` | Notas |
  |---|---|---|
  | Resistencias | `rgba(239,83,80,0.45)` | |
  | Soportes | `rgba(38,166,154,0.45)` | |
  | Pivote | `rgba(255,179,0,0.75)` | linewidth 3. Va mas marcado a proposito: es el nivel que define |
  | Directriz | `rgba(150,150,150,0.40)` | punteada |

  Etiquetá cada linea con `showLabel:true` y un `text` corto (ej. `S1 43.50 piso triple`).
  **El `textcolor` va aparte y sin alfa** (`#ef5350`, `#26a69a`, `#ffb300`): la linea se
  atenua, la etiqueta tiene que seguir legible.
- **Zona critica** alrededor del pivote: un `rectangle` azul con borde
  `rgba(41,98,255,0.35)` y fondo transparente.
- **Directriz bajista** desde el maximo de 58.14 (18-jun-2026) hasta 40.63 (21-sep):
  `trend_line` gris punteada (`rgba(150,150,150,0.40)`, ver la tabla de arriba). OJO: TradingView la plotea en espacio de **barras**,
  no de tiempo lineal — para saber por donde pasa hoy, interpolá por indice de
  barra, no por dias calendario (interpolar por calendario da ~0.35 de mas).
- Dejá el chart con un rango visible de las ultimas ~40 ruedas y sacá el
  screenshot con nombre `ggal_TURNO_FECHA`. Si `document.hidden` es `true`,
  `capture_screenshot` sale en blanco (paso en 8 de las primeras 12 corridas):
  usá `TradingViewApi.takeClientScreenshot()` + descarga.
- Para guardar el layout, `saveChart()`: `saveChartSilently` ya no existe.

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
- **Todo gatillo es un cierre.** Escribí "cierre arriba/debajo de X", nunca
  "superar X" o "perder X" a secas: un toque intradia no activa nada. Si el
  gatillo es el maximo o el minimo de una vela de rotura, avisá que es el nivel
  mas probable de trampa.
- **Contra la tendencia** (precio del otro lado de la EMA20 y serie de
  maximos/minimos intacta), un gatillo recien cuenta como confirmado con **dos
  cierres seguidos** del otro lado del nivel. Con un solo cierre escribilo como
  "rebote en curso, sin confirmar", no como escenario activado. A favor de la
  tendencia vale con un cierre. (Auditoria 2026-09-24: los gatillos a favor de la
  tendencia anduvieron 4 de 4; los en contra, 0 de 6.)
- **En la apertura no inclines el sesgo por la vela en curso.** Los escenarios se
  arman sobre el ultimo cierre; la vela de hoy se describe, pero no mueve la
  balanza. (En 3 de las primeras 5 aperturas el signo al cierre fue el opuesto al
  de la lectura.)
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
