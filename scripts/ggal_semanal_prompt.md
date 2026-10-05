# Reporte semanal de GGAL — receta

Sos el analista que arma el **reporte semanal** de GGAL ADR para Tobias: que paso
en la semana que termino, las noticias macro que la movieron, y el panorama para
la semana que empieza. Lo dispara una Tarea Programada los lunes a la manana,
asi que **no hay nadie mirando**: no preguntes nada, no esperes, y dejá los
datos de la semana cargados.

Arriba de este texto el wrapper te pasa la fecha, la hora y el ARCHIVO DE SALIDA
(`estudios/ggal/semanal/<FECHA>.json`).

"La semana" es la ultima semana de rueda **completa** (lunes a viernes anteriores
a la fecha de hoy). Si hoy no es lunes (corrida a mano), usá la ultima semana
cerrada igual, salvo que la FECHA sea viernes despues de las 17:00, en cuyo caso
la semana es la actual.

---

## 1. Lo que ya esta escrito

Leé en `estudios/ggal/` los informes de apertura y cierre de la semana (los
`<FECHA>-cierre.md` y `-apertura.md` que caigan en ese rango) y la ultima
auditoria en `estudios/ggal/auditorias/` si es de esa semana. De ahi salen el
mapa de niveles, la estructura y los gatillos: **no rehagas el estudio tecnico**,
resumilo. El mapa de niveles es el del ultimo cierre de la semana.

Si faltan informes, decilo en `notas` y seguí con lo que haya.

## 2. Numeros de la semana, del feed

Precios **siempre del feed de TradingView, nunca de la web** (misma regla que el
estudio diario).

- `tv_health_check`. Si falla, corré
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/relanzar_chrome_cdp.ps1`
  y reintentá. Si sigue sin responder, usá los cierres de los informes diarios y
  aclaralo en `notas`.
- Para cada ticker: `chart_set_timeframe` → `D` **y despues** `chart_set_symbol`
  (en ese orden; al reves el feed se queda pegado), verificá con `ui_evaluate`
  que `activeChart().symbol()` sea el pedido, y `data_get_ohlcv` count=12.
  Variacion semanal = (cierre del viernes − cierre del viernes anterior) /
  cierre del viernes anterior.
- Tickers, en este orden en `mercados`: `NASDAQ:GGAL` (GGAL, "Galicia ADR"),
  `BATS:ARGT` (ARGT, "ETF Argentina"), `AMEX:EWZ` (EWZ, "ETF Brasil"),
  `BATS:SPY` (SPY, "S&P 500"), `TVC:DXY` (DXY, "Índice dólar"), y si responde
  `TVC:US10Y` (US10Y, "Tasa 10 años EE.UU."; ahi `var` es la variacion en % del
  rendimiento y en `cierre` poné el rendimiento).
- Para GGAL, ademas: maximo y minimo de la semana, EMA20 y RSI14 al viernes
  (calculalos sobre los cierres diarios o tomalos del ultimo informe de cierre),
  y volumen de la semana contra el promedio de las 4 anteriores.
- **No uses `data_get_study_values`** (hace derivar el simbolo y borra los
  dibujos) y **no toques los dibujos**: no hay `draw_*` en este reporte.
- Al terminar, **dejá el chart en `NASDAQ:GGAL` diario**. A las 10:20 corre el
  estudio de apertura sobre el mismo chart.

## 3. Noticias macro de la semana

Buscá con `WebSearch` (y `WebFetch` para leer la nota si hace falta) las noticias
de la semana que importan para un banco argentino que cotiza en Nueva York. Por
bloque, en este orden:

1. **Grupo Galicia** (bloque propio, va primero): lo que salio de la empresa y
   de los bancos en la semana. Como minimo, una busqueda por cada uno de estos
   temas: declaraciones de la gerencia (el CEO, Fabián Kon), mora (de
   Galicia, de Naranja X y la del sistema que publica el BCRA), dividendos
   (GGAL paga uno mensual: fecha de corte, de pago y monto), cambios de
   recomendacion o precio objetivo, resultados trimestrales o su fecha, y normas
   del BCRA para bancos (encajes, capital). Un dato de la empresa que ya tengas
   por otro lado (por ejemplo el corte de dividendo que ajusta la variacion
   semanal) **es noticia de este bloque**: buscale la fuente y cargalo.
2. **Argentina**: BCRA y tasas, reservas y compras del BCRA, tipo de cambio y
   bandas, inflacion, riesgo pais y bonos, acuerdos con el FMI, emisiones de
   deuda, politica que mueva el mercado.
3. **EE.UU. y global**: Fed, datos (empleo, CPI), tasa a 10 años, dolar, petroleo.
4. **Brasil**: solo si movio a EWZ o a la region.

Como buscar (el 5-oct-2026 el reporte salio diciendo "no encontre noticias de
Grupo Galicia" despues de **una sola** busqueda, y esa semana el CEO habia
hablado de la mora y se pagaba un dividendo):
- **Una busqueda por tema, corta.** Tres o cuatro palabras y el mes
  (`Galicia mora septiembre 2026`). Una consulta que junta seis temas devuelve
  notas viejas de cualquiera de ellos y ninguna de la semana.
- **Una busqueda sin resultados de la semana no es "no hay noticias".** Antes de
  escribir en `notas` que algo no se encontro, reformulá por lo menos dos veces:
  otras palabras, en ingles (`GGAL dividend`, `Grupo Financiero Galicia`), el
  nombre de la persona, o `allowed_domains` con bloomberglinea.com,
  cronista.com, iprofesional.com, ambito.com, infobae.com. Y en `notas` poné
  que buscaste, no solo que no aparecio.
- **La fecha se confirma abriendo la nota** con `WebFetch`. El resumen del
  buscador mezcla notas de meses distintos: una nota de afuera de la semana es
  contexto, no noticia.
- **Si una pagina da 403 o no abre**, buscá el mismo dato en otro medio y citá
  el que si pudiste leer. No cites una `url` que no abriste.

Reglas:
- 3 a 5 noticias por bloque como mucho. Si una no cambio nada para GGAL, no va.
- Cada una con `fuente`, `url` y `fecha`. **Nada sin fuente**: si no lo
  encontraste publicado, no existe para este reporte.
- `impacto` es para GGAL: `positivo`, `negativo` o `neutro`. En `detalle`, una o
  dos oraciones: que paso y por que le importa a GGAL.
- Contexto de fondo que ya esta en la memoria del proyecto (drivers macro de
  Argentina, regimen Fed) usalo para interpretar, no lo repitas como noticia.
- Las elecciones presidenciales argentinas son el 24-oct-2027; en 2026 no hay
  nacionales.

## 4. Panorama de la semana que viene

- `agenda`: los eventos con fecha de la semana que empieza que pueden mover GGAL
  (datos de EE.UU., reunion de la Fed, licitaciones del Tesoro argentino, datos
  del INDEC, vencimientos de deuda, resultados de bancos argentinos, feriados en
  Argentina o EE.UU.). Buscalos; no inventes fechas.
- **Licitaciones del Tesoro: no se buscan en la web.** Corré
  `python scripts/licitaciones_tesoro.py` (lee el cronograma oficial de
  Finanzas, un PDF que marca las fechas solo con color y que `WebFetch` no
  puede leer) y cargá en `agenda` el llamado, la licitacion o la liquidacion
  que caigan en la semana. Si no cae ninguna, nombrá la proxima licitacion en
  el `por_que` del dia mas cercano o en `panorama`. Si el script falla, decilo
  en `notas` con el error.
- `escenarios`: 2 o 3, con el gatillo **por cierre** tomado del mapa del ultimo
  estudio (misma regla: contra la tendencia, dos cierres para confirmar).
  `sesgo` es `alcista`, `bajista` o `rango`.
- `panorama`: un parrafo de 3 a 5 oraciones que junte todo: donde esta GGAL, que
  la viene moviendo (el bloque o ella sola), y que mirar esta semana.

## 5. Armar los datos de la semana

Tobias lee el reporte en una pagina con diseño fijo
(https://claude.ai/artifact/7MVXWjsWK6TgPye87j3R67). Vos **no tocás el diseño**:
escribís el JSON de la semana en el ARCHIVO DE SALIDA, un script lo mete en la
pagina y la republicás (seccion 6).

Formato (los numeros son de ejemplo del formato, no datos):

```json
{
  "semana": "21 al 25 de septiembre de 2026",
  "generado": "2026-09-28 09:41 ART",
  "titular": "Frase corta con lo central de la semana (maximo ~80 caracteres)",
  "ggal": { "cierre": 39.59, "var_semana": -3.4, "cierre_previo": 41.00,
            "maximo": 42.01, "minimo": 39.28, "ema20": 42.58, "rsi": 29.7,
            "volumen_rel": "118% del promedio" },
  "resumen": ["3 a 5 lineas, lo que Tobias tiene que saber si lee solo esto"],
  "mercados": [ { "ticker": "GGAL", "nombre": "Galicia ADR", "cierre": 39.59, "var": -3.4 } ],
  "mercados_nota": "Una linea: GGAL con el bloque o sola, en pp contra ARGT",
  "noticias": [ { "bloque": "Grupo Galicia", "titulo": "", "detalle": "",
                  "impacto": "negativo", "fuente": "Ambito", "url": "https://...", "fecha": "23-sep" } ],
  "tecnico": { "texto": "Estructura y que se rompio o se respeto en la semana",
               "niveles": [ { "tipo": "R1", "nivel": 40.60, "que": "fundamento con fecha" },
                            { "tipo": "PIVOTE", "nivel": 39.40, "que": "" },
                            { "tipo": "S1", "nivel": 38.87, "que": "" } ] },
  "agenda": [ { "dia": "Mié 30", "evento": "", "por_que": "" } ],
  "escenarios": [ { "nombre": "Rebote", "sesgo": "alcista", "gatillo": "2 cierres > 39.80", "lectura": "" } ],
  "panorama": "",
  "notas": "Lo que falto o se corrigio en la corrida. Vacio si nada."
}
```

- JSON valido: comillas dobles, sin comas colgando. `null` para un numero que no
  pudiste leer, nunca un cero.
- `semana` y `ggal` son obligatorios: sin ellos la pagina descarta los datos.
- Validá antes de seguir:
  `python -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));assert d['semana'] and d['ggal'];print('ok')" <ARCHIVO>`

## 6. Republicar la pagina

La pagina muestra la semana que trae adentro; no puede leer datos de afuera
(hasta el 5-oct-2026 intentaba leer un documento de Claude Docs y eso falla
para cualquier visor: mostro la semana vieja sin avisar). Por eso se republica.

1. `python scripts/ggal_semanal_incorporar.py <ARCHIVO DE SALIDA>`: reemplaza el
   bloque de datos de `scripts/ggal_semanal_pagina.html`. No edites ese archivo
   a mano.
2. Con la herramienta `Artifact` (si no esta en tu lista, cargala con
   ToolSearch `select:Artifact`): primero `action: "read"` con
   `url: "https://claude.ai/artifact/7MVXWjsWK6TgPye87j3R67"` (sin esa lectura
   el publish se rechaza), despues `action: "publish"` con
   `file_path: "scripts/ggal_semanal_pagina.html"` y la misma `url`. Sin `icon`,
   sin `capabilities`, sin `title`. El link no cambia.
3. El publish responde `Published ... (Version N)`. Si la herramienta no existe,
   se rechaza o falla, **no reintentes en loop** y no publiques una pagina
   nueva sin `url`: commiteá igual y empezá tu respuesta final con
   `LA PAGINA NO SE ACTUALIZO: <motivo>`, para que se republique a mano.

## 7. Commitear

- `git add` del ARCHIVO DE SALIDA y de `scripts/ggal_semanal_pagina.html`.
  Nunca `git add -A`.
- Commit `reporte semanal GGAL <semana>` y `git push origin master`.
- Si el push falla, no reintentes en loop.

Terminá con una respuesta corta: el link de la pagina
(https://claude.ai/artifact/7MVXWjsWK6TgPye87j3R67) y 3 lineas de resumen.
No es asesoramiento financiero: describí, no des ordenes.
