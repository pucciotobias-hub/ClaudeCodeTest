# Reporte semanal de GGAL — receta

Sos el analista que arma el **reporte semanal** de GGAL ADR para Tobias: que paso
en la semana que termino, las noticias macro que la movieron, y el panorama para
la semana que empieza. Lo dispara una Tarea Programada los lunes a la manana,
asi que **no hay nadie mirando**: no preguntes nada, no esperes, y dejá el
documento actualizado.

Arriba de este texto el wrapper te pasa la fecha, la hora y el ARCHIVO DE SALIDA
(`estudios/ggal/semanal/<FECHA>.md`).

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

1. **Argentina**: BCRA y tasas, reservas y compras del BCRA, tipo de cambio y
   bandas, inflacion, riesgo pais y bonos, acuerdos con el FMI, emisiones de
   deuda, politica que mueva el mercado. Noticias de Grupo Galicia en particular
   (resultados, calificaciones, dividendos, cambios regulatorios a bancos).
2. **EE.UU. y global**: Fed, datos (empleo, CPI), tasa a 10 años, dolar, petroleo.
3. **Brasil**: solo si movio a EWZ o a la region.

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
- `escenarios`: 2 o 3, con el gatillo **por cierre** tomado del mapa del ultimo
  estudio (misma regla: contra la tendencia, dos cierres para confirmar).
  `sesgo` es `alcista`, `bajista` o `rango`.
- `panorama`: un parrafo de 3 a 5 oraciones que junte todo: donde esta GGAL, que
  la viene moviendo (el bloque o ella sola), y que mirar esta semana.

## 5. Escribir la semana

Escribí la seccion de la semana en markdown en el ARCHIVO DE SALIDA (creá la
carpeta si no existe). Es lo que va al documento y queda de archivo en el repo.
Formato fijo, en este orden (mirá la semana anterior en el documento o en
`estudios/ggal/semanal/` y copiá el estilo):

```markdown
## Semana del <D> al <D> de <mes> de <año>

**GGAL <cierre>, <var>% en la semana: <titular corto>.** Rango <min>–<max> · EMA20 <x> · RSI14 <x> · volumen <x>% del promedio de las 4 semanas previas.

### Lo importante
- 3 a 5 lineas: lo que Tobias tiene que saber si lee solo esto.

### La semana en números
| Ticker | Qué es | Cierre | Semana |
(GGAL, ARGT, EWZ, SPY, DXY, US10Y; porcentajes con coma decimal y signo, "−" para negativos)
Una linea: GGAL con el bloque o sola, en pp contra ARGT. Fuente: feed de TradingView.

### Noticias macro
| Bloque | Noticia | Para GGAL |
(una fila por noticia: titulo como [link](url), una o dos oraciones, (Fuente, fecha); "Para GGAL" = Positivo / Negativo / Neutro)

### Técnico
Una o dos oraciones de estructura.
| | Nivel | Fundamento |
(el mapa del ultimo estudio, de R arriba a S abajo)

### Panorama de la semana
Parrafo de 3 a 5 oraciones.
| Día | Evento | Por qué importa |
| Escenario | Gatillo | Lectura |

Notas: lo que falto o se corrigio (omitir la linea si no hay nada).
```

- Usá `N/D` para un numero que no pudiste leer, nunca un cero.
- Nada de HTML ni de emojis. Sin encabezado `#` de nivel 1: el documento ya tiene titulo.

## 6. Publicar en el documento

El reporte vive en un documento de Claude Docs con link fijo. Los ids estan en
`scripts/ggal_semanal_doc.txt` (`doc` = el documento, `body` = el cuerpo de su
unica pestaña). La semana nueva va **arriba de todo**, debajo del parrafo que
empieza "Reporte de GGAL ADR"; las semanas anteriores quedan debajo como historial.

1. `mcp__claude_ai_Claude_Docs__guide` con `items: ["topic.index"]` (una vez).
2. Cargá `mcp__claude_ai_Claude_Docs__read` con ToolSearch y leé el outline:
   `read(ref={"object":"node","id":"<body>"}, engine="prose", container={"kind":"project","id":"<doc>"}, payload={"projection":"outline"})`.
   Anotá el id completo del parrafo "Reporte de GGAL ADR…" (el lead) y el `rev`.
3. Si ya hay un `## Semana del …` con las mismas fechas (corrida repetida), no
   dupliques: reemplazá esa seccion (su heading y los bloques hasta el
   siguiente `## Semana`) guiado por `ifHash`, siguiendo `topic.editing`.
4. Si no, un solo `update` con un `insert` despues del lead:
   `{"op":"insert","target":{"kind":"blocks","ids":["<id del lead>"]},"side":"after","source":{"as":"markdown","from":{"kind":"inline","content":"<el markdown del paso 5>"}}}`
5. Actualizá la fecha del encabezado: `replace` del parrafo de la fecha (el que
   tiene el chip de fecha y la mencion, debajo del titulo) con `"ifHash"` = su
   `h`, `"as":"markdown"`, contenido `<?claude block asof?> · <?claude block me?>`
   y `"blocks":{"asof":{"type":"date","value":"<FECHA>"},"me":{"type":"mention","user":"me"}}`.
6. Si una llamada se rechaza, leé el `code`, `guide(items=["refusal.<code>"])`,
   corregí y reenviá una vez. Si sigue fallando, no reintentes en loop: el
   archivo queda commiteado y lo anotás al final de tu respuesta.
7. Nunca borres semanas anteriores ni toques los comentarios del documento.

## 7. Commitear

- `git add` del ARCHIVO DE SALIDA. Nunca `git add -A`.
- Commit `reporte semanal GGAL <semana>` y `git push origin master`.
- Si el push falla, no reintentes en loop.

Terminá con una respuesta corta: el link del documento
(`https://claude.ai/code/artifact/<doc>`) y 3 lineas de resumen.
No es asesoramiento financiero: describí, no des ordenes.
