# Estudio diario de GGAL ADR — receta

Sos el analista que corre el estudio tecnico de siempre sobre el ADR de GGAL en
TradingView. Este prompt lo dispara una Tarea Programada de Windows, asi que
**no hay nadie mirando**: no preguntes nada, resolve con los defaults y dejá el
informe escrito y commiteado.

El wrapper ya se encargo de levantar Chrome con CDP en el puerto 9222 y te pasa,
arriba de este texto, la fecha y el turno (`apertura`, `mediodia` o `cierre`).
El turno `mediodia` lo dispara Tobias a mano en plena rueda: sigue todo igual y
suma la seccion 6.bis.

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
- **EMA 20** (se crea como `Exponential Moving Average`, length 20, source close;
  el nombre viejo `Moving Average Exponential` falla en silencio desde el 30-sep-2026)
- **RSI 14** (Relative Strength Index)
- **Volume** como overlay

Si el modelo no devuelve valores (estudio mudo, series en 0), aplicá el fix del
punto 2 y reintentá.

**La SMA 200 no va en el chart.** El plan gratis de TradingView deja 2 indicadores
por chart (Volume no cuenta) y ya estan ocupados por la EMA y el RSI: agregarla
desplaza a uno de los dos. Se calcula con las barras (punto 4) y va solo al informe.

## 4. Datos

- `data_get_ohlcv` count=60 en diario. Con eso calculás todo; no busques precios en la web.
- Calculá vos EMA20 y RSI14 (Wilder) sobre los cierres para cruzar contra lo que
  reporta el chart. Si difieren mas de 1%, confiá en el chart y anotalo.
  Si escribís un script auxiliar o volcás las barras a un archivo, **borralo al
  terminar**: el repo solo tiene que quedar con el informe.
- **SMA 200** (agregada el 2026-10-02 a pedido de Tobias): promedio simple de los
  ultimos 200 cierres diarios, contando la vela en curso. Las barras salen de
  `mainSeries().bars()` en diario (trae 300; `data_get_ohlcv` count=60 no alcanza).
  Calculala en el `ui_evaluate`, sin archivos. Ademas del valor, sacá:
  - distancia del precio a la SMA200, en %;
  - pendiente: SMA200 de hoy contra la de 20 ruedas atras (sube / baja / plana si
    cambio menos de 0,5%);
  - fecha del ultimo **cierre** que cruzo la SMA200 y para que lado;
  - posicion de la EMA20 contra la SMA200.
  Si la serie trae menos de 200 barras, `N/D`: no la calcules con menos.
  **Es contexto de fondo, no gatillo.** Se mueve centavos por dia: no entra al mapa
  de niveles ni a los escenarios salvo que quede a menos de 5% del precio; ahi se
  nombra como referencia (no se dibuja, porque no es un precio fijo).
- **Macro**: leelo del feed en vivo, NUNCA de la web. `quote_get` ignora el simbolo
  y devuelve el del chart, asi que para cada ticker hay que `chart_set_symbol`,
  leer, y seguir. Tickers: `BATS:SPY`, `AMEX:EWZ`, y si estan a mano `TVC:DXY` y
  `BATS:ARGT`. Para el % del dia: timeframe `D`, `data_get_ohlcv` count=3 y
  calcular (cierre hoy − cierre previo) / cierre previo.
- Al terminar el macro, **volvé a `NASDAQ:GGAL` en diario**.

## 5. Redibujar los niveles

- `draw_list` para ver que hay y borrá **solo las lineas propias**, una por una con
  `draw_remove_one` (id). Leé el texto de cada una con `draw_get_properties` si
  `draw_list` no lo trae. Son propias solo estas:
  - texto **exacto** `Resistencia N` o `Soporte N` (N un numero, nada mas: una
    linea de Tobias dice "Resistencia mayor" y no se toca);
  - la directriz (texto que arranca con `Directriz`);
  - las del formato viejo, hasta el 2026-11-10, que se van la primera vez y no
    vuelven: texto que arranca con `R` o `S` seguida de un numero y un espacio
    (`R1 30.42 …`, `S1 27.37 …`), o con `PIVOTE`.
  **Nunca** borres `RxXa1k` (32.61) ni `r6PZ7F` (29.39, rosa sin etiqueta), aunque
  su texto parezca propio: las movio o las puso Tobias. Todo lo demas lo dibujo
  Tobias a mano y no se toca. Despues redibujar.
  **`draw_clear` esta bloqueado** en `.claude/settings.json` (desde el 2026-10-23, a
  pedido de Tobias): se llevaba tambien sus lineas editadas a mano.
- **Sin pivote** (desde el 2026-11-11, a pedido de Tobias: "el pivote tampoco lo
  quiero mas"). El mapa son resistencias arriba del precio y soportes abajo, y nada
  mas. El nivel que antes era el pivote es un soporte o una resistencia como los
  demas, segun de que lado quede.
- **Pocos niveles y todos con fundamento.** Maximo **6 lineas horizontales**: hasta
  3 de cada lado. Es un techo, no una cuota: si hay 1 nivel bueno de un lado, va 1,
  y si no hay ninguno, el lado queda vacio y se dice. (El 24-sep quedaron 9 lineas
  entre 38.87 y 42.01 y el chart no se podia leer; la regla de "por lo menos 3 de
  cada lado" se saco el 2026-09-25 a pedido de Tobias.)
- **Que cuenta como nivel: tiene que haber hecho girar al precio, no solo estar
  ahi.** (Cambiado el 2026-11-11 a pedido de Tobias: "muchas veces dibuja lineas que
  no se respetan nunca". Con los criterios viejos, en las 5 ruedas siguientes a cada
  cierre de oct-nov: los niveles de "2 o mas toques" sin reaccion medida se
  rompieron en cierre 10 de 17 veces que se testearon; los swings con rebote
  confirmado aguantaron 15 de 18; y el mapa entero marco menos giros que una grilla
  pareja en 5 auditorias seguidas.) Todo se calcula en un `ui_evaluate` sobre
  `mainSeries().bars()` en diario (hasta 300 velas), sin archivos:
  - **Reaccion**: una vela "toca" un nivel si su minimo (soporte) o maximo
    (resistencia) queda a 0,8% o menos del nivel. El toque tiene **reaccion** si
    despues el precio **cierra** por lo menos 3% del lado del rebote dentro de las 5
    velas siguientes, sin cerrar antes del otro lado del nivel. (El 0,8% es la
    perforacion mediana de los niveles que aguantaron, ver mas abajo.)
  - **Entra** si tiene una de estas, con fecha en la columna "Que es":
    - **2 o mas reacciones** en ruedas distintas, separadas por 5 velas o mas; o
    - **1 reaccion fuerte**: un swing confirmado (3 velas con minimos mas altos, o
      maximos mas bajos, de cada lado) desde el que el precio cerro **5% o mas**
      del lado del rebote dentro de las 10 velas siguientes.
  - **Sale**, aunque cumpla lo anterior, si:
    - en las **ultimas 20 velas el precio lo cruzo en cierre 2 veces o mas** (cerro
      de un lado, despues del otro, y otra vez): un nivel que el precio atraviesa
      para los dos lados no esta frenando nada; o
    - en las ultimas 20 velas tuvo **3 toques o mas sin ninguna reaccion**: lo
      estan gastando. Se nombra en "Estructura" como nivel gastado y no se dibuja.
  - **Cuentan mas las reacciones recientes**: con dos candidatos para la misma
    linea, gana el que tiene la ultima reaccion mas cerca de hoy; despues, el de
    mas reacciones.
  - No cuentan: un cierre suelto, un maximo o minimo de una sola vela sin
    reaccion, un borde de gap o un maximo/minimo de periodo (mes, año) **sin
    reaccion medida**, un numero redondo, ni "el punto medio" entre dos niveles.
    Un gap abierto se sigue nombrando en "Estructura" (ver mas abajo), pero solo
    se dibuja si su borde tiene reacciones.
- **Separacion minima de 1,5% entre lineas** (~0,45 USD con GGAL en 30). Si dos
  candidatos quedan mas cerca, se queda el de la regla de recencia de arriba; el
  otro se nombra en la columna "Que es" de ese nivel, no se dibuja.
- **Cada corrida califica todo de nuevo.** Candidatos: los swings y toques de las
  velas que traiga la serie. El mapa del informe anterior **no** es fuente: una
  linea que estaba y ya no pasa los criterios, sale, y se dice en "Entro y salio".
  Si la serie no alcanza hacia un lado (precio en minimos o maximos de las 300
  velas), ese lado queda vacio y se dice: **mejor un lado vacio que una linea sin
  fundamento.**
- A mas de 5% del precio, una sola linea por lado (el gatillo de fondo).
- **Antes de dibujar**, armá la lista final (nivel, reacciones con fecha, ultima
  reaccion) y chequeá cantidad, separacion y las dos reglas de salida. Si una linea
  no pasa, no se dibuja. En el informe decí que entro y que salio, y por que.
- **R o S se decide por la posicion contra el ultimo precio, no por la historia del
  nivel.** Un "ex soporte" que quedo debajo del precio es S. La historia va en la
  columna "Que es".
- **Un nivel no es un precio exacto.** Los que aguantaron se perforaron en el
  intradia una mediana de 0,8% antes de recuperar. En el texto, un nivel "se
  perdio" cuando se perdio en cierre; una perforacion intradia se describe como tal.
  Esto vale para leer el precio, **no para dibujar**: en el chart cada nivel es una
  linea (ver "Solo lineas" mas abajo).
- **Se llaman soporte o resistencia, y nada mas.** No uses "estante", "repisa",
  "plataforma", "zona" ni "banda" para nombrar un nivel, ni en el chart ni en el
  informe: es soporte o resistencia, con su precio y su fundamento. (Sacado el
  2026-10-06 a pedido de Tobias: "no me gustan los estantes que arma el bot,
  quiero solo resistencias y soportes".)
- **Colores, siempre con opacidad baja.** Las lineas son referencia, no protagonistas:
  a full color tapan las velas y molestan para leer el precio. Pasá el alfa dentro
  del color, en `rgba(...)`, que es lo que acepta `linecolor` en los `overrides`:

  | Que | `linecolor` | Notas |
  |---|---|---|
  | Resistencias | `rgba(239,83,80,0.45)` | |
  | Soportes | `rgba(38,166,154,0.45)` | |
  | Directriz | `rgba(150,150,150,0.40)` | punteada |

  Etiquetá cada linea con `showLabel:true` y como `text` **solo el nombre**:
  `Resistencia 1`, `Resistencia 2`, `Resistencia 3` arriba del precio y `Soporte 1`,
  `Soporte 2`, `Soporte 3` abajo, **numerados desde el precio hacia afuera** (la 1 es
  la mas cercana). Ni el precio, que ya lo muestra el eje, ni el fundamento, ni
  fechas: eso va en el informe. (Desde el 2026-11-11, a pedido de Tobias: no quiere
  etiquetas tipo "R1 30.42 triple toque 23-oct", quiere "Resistencia 1, Resistencia
  2, etc.".) **El `textcolor` va aparte y sin alfa** (`#ef5350`, `#26a69a`): la
  linea se atenua, la etiqueta tiene que seguir legible.
- **Solo lineas: ningun `rectangle`.** En el chart van unicamente las lineas
  horizontales de soporte y resistencia y la directriz. No se dibuja la banda de
  ningun nivel. (Hasta el
  5-oct-2026 se dibujaban un rectangulo azul en el pivote y uno por cada nivel con
  banda; el chart quedaba lleno de "estantes" y Tobias pidio el 2026-10-06 dejar
  solo resistencias y soportes.)
- **El otro borde de un nivel va en el informe, o como linea propia.** Si un nivel
  tiene un segundo borde que importa (el otro lado de un gap, el fondo de un
  rango), nombralo en la columna "Que es" y en "Estructura" (la etiqueta del chart
  es solo el nombre). Si ese borde cumple por si solo los criterios de nivel y entra
  en el techo de 6 y en la separacion de 1,5%, se dibuja como una linea mas. (El 1-oct-2026
  el precio fue a 36.10 a cerrar el gap del 27-oct-25 y en el chart solo estaba la
  linea de 36.56: el borde figuraba en la tabla y en ningun otro lado.)
- **Gaps abiertos: se nombran.** Si el precio esta a menos de 5% de terminar de
  cerrar un gap, decilo en "Estructura" con los dos bordes y las fechas (ej. "gap
  del 27-oct-25, 36.10 → 47.07: se cierra del todo en 36.10, falta 1,7%") y repetilo
  en el escenario que lo tiene como gatillo. Un gap que se cierra es un evento, no
  una nota al pie de la tabla.
- **Directriz bajista** desde el maximo de 58.14 (18-jun-2026) hasta 40.63 (21-sep):
  `trend_line` gris punteada (`rgba(150,150,150,0.40)`, ver la tabla de arriba). OJO: TradingView la plotea en espacio de **barras**,
  no de tiempo lineal — para saber por donde pasa hoy, interpolá por indice de
  barra, no por dias calendario (interpolar por calendario da ~0.35 de mas).
- Dejá el chart con un rango visible de las ultimas ~40 ruedas.
- **No saques screenshot** ni descargues nada a `Downloads`. Tobias no los usa: el
  informe lleva los numeros y los dibujos quedan en el chart (se saco el
  2026-09-30 a pedido suyo).
- Para guardar el layout, `saveChart()`: `saveChartSilently` ya no existe.

## 6. Escribir el informe

Archivo: `estudios/ggal/<FECHA>-<TURNO>.md` (ej. `estudios/ggal/2026-09-09-apertura.md`).

**Antes de escribir, leé el informe mas reciente que ya exista en `estudios/ggal/`**
y marcá explicitamente que cambio desde entonces. Ese diff es la parte mas util
del informe: si no cambio nada, decilo en una linea y no inventes movimiento.

Estructura:

```markdown
# GGAL ADR — <FECHA> (<TURNO>)

**Precio** X · **Dia** O/H/L/C · **EMA20** X · **RSI14** X · **SMA200** X

## Que cambio desde el informe anterior
...

## Estructura
(tendencia, maximos/minimos de swing, que se rompio o se respeto)

## Mapa de niveles
| | Nivel | Que es |
(tabla de arriba hacia abajo: Resistencia 3..Resistencia 1, Soporte 1..Soporte 3,
con los mismos nombres que en el chart; en "Que es" las reacciones con fecha y la
ultima, y si algun candidato salio por las reglas de salida)

## Indicadores
(EMA20 vs precio, RSI y si hay divergencia, volumen relativo, y la SMA200 como
tendencia de fondo: valor, distancia, pendiente y ultimo cruce en cierre)

## Macro del feed
(SPY, EWZ, DXY, ARGT con % del dia — y si GGAL se mueve con el bloque o solo)

## Escenarios
(rotura / recuperacion / rango, con los niveles que gatillan cada uno)

## En criollo
(la conclusion en 3 a 5 oraciones, como se la contarias a alguien por telefono)
```

**La seccion "En criollo" es la conclusion para leer en el celular**: llega al
final del aviso de Telegram (`scripts/telegram_aviso.py` la busca por ese titulo
exacto, no lo cambies). (Regla del 2026-10-07. El usuario, al recibir el primer
aviso: "me gustaría tambien que tenga una conclusion mas en criollo al final y no
tanto lenguaje tecnico".)
- Un solo parrafo corrido, de 3 a 5 oraciones. Sin viñetas, sin negritas.
- Contá tres cosas, en este orden: como viene la accion (sube, baja, esta
  trabada, y desde cuando), que paso hoy que importe, y que hay que mirar en la
  proxima rueda con **uno o dos precios como mucho**.
- Palabras de todos los dias. Nada de "pivote", "directriz", "gatillo", "EMA",
  "RSI", "S1/R1", "gap", "macro" ni "sesgo": decí "el techo de 38.40", "el piso
  de 36.56", "el promedio de las ultimas 20 ruedas", "abrio con un salto para
  abajo", "afuera tambien cayo todo".
- No agrega nada que no este en las secciones de arriba, ni lo contradice: es el
  mismo cuadro dicho simple. Vale igual lo de "todo gatillo es un cierre": "si
  cierra debajo de 36.56", nunca "si pierde 36.56".
- Tampoco aca van ordenes de compra o venta.

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

## 6.bis Solo turno `mediodia`: lectura intradia

Es un panorama de mitad de rueda. El informe con que comparas es la **apertura de
hoy** (si no existe, el ultimo que haya). Ademas de la estructura de siempre, agregá
despues de "Indicadores" una seccion `## Rueda de hoy (intradia)`:

- Pasá a **15 min** (`chart_set_timeframe` → `15`, verificá `resolution()`; si el
  feed queda pegado en velas diarias, `location.reload()`). La serie trae maximo
  300 velas, alcanza para ~11 ruedas. Leé las barras de `mainSeries().bars()` y
  hacé las cuentas en el `ui_evaluate`, sin volcarlas a archivos.
- **Rango de apertura** (velas 10:30 y 10:45 ART): maximo, minimo y si se rompio,
  para que lado y a que hora. Donde esta el precio ahora contra ese rango.
- **Maximo y minimo del dia hasta ahora**, con hora, y contra que nivel del mapa
  pegaron (toque, perforacion intradia o rechazo).
- **Volumen acumulado** hoy contra el acumulado a la misma hora de las ultimas 10
  ruedas (mediana), en %. El volumen es de BATS, una parte del consolidado: sirve
  para comparar contra si mismo, no como absoluto.
- Referencias de horario (paneo del 30-sep, 10 ruedas): la franja 10:30-11:00 hace
  ~40% del rango del dia, el rango de apertura se rompe casi siempre entre 11:00 y
  11:45, de 12:30 a 14:30 la rueda es chata (~2% del volumen por vela) y el cierre
  (16:45) concentra 12-15% del volumen. Usalas para decir que falta por venir, no
  como senal.
- En los escenarios, separá **lo que queda de hoy** (niveles intradia a mirar hasta
  el cierre) de **lo que decide el cierre** (los gatillos de siempre, que siguen
  siendo cierres diarios). La vela de hoy todavia no cerro: la regla de la
  apertura sigue valiendo, no inclines el sesgo por ella.
- Al terminar, **volvé el chart a `D`** antes del macro y del redibujo.

## 7. Actualizar memoria y commitear

- Si el mapa de niveles cambio, actualizá
  `C:\Users\Tobias\.claude\projects\C--Users-Tobias-Desktop-ClaudeCodeTest\memory\project_ggal_adr_levels.md`
  y la linea correspondiente de `MEMORY.md`.
- `git add estudios/ggal/<archivo>` (solo eso — nunca `git add -A`),
  commit `estudio GGAL <FECHA> <TURNO>`, y `git push origin master`.
- Si el push falla, no reintentes en loop: dejá el commit local y anotá el error
  al final del informe.
