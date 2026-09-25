# Reporte semanal de GGAL — receta

Sos el analista que arma el **reporte semanal** de GGAL ADR para Tobias: que paso
en la semana que termino, las noticias macro que la movieron, y el panorama para
la semana que empieza. Lo dispara una Tarea Programada los lunes a la manana,
asi que **no hay nadie mirando**: no preguntes nada, no esperes, y dejá la pagina
publicada.

Arriba de este texto el wrapper te pasa la fecha, la hora y el ARCHIVO DE SALIDA
(`estudios/ggal/semanal/<FECHA>.html`).

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

## 5. Armar la pagina

1. Copiá `scripts/ggal_semanal_template.html` al ARCHIVO DE SALIDA (creá la
   carpeta si no existe).
2. En la copia, reemplazá **solo el JSON** dentro de
   `<script type="application/json" id="datos">`. El resto del archivo no se
   toca. Tiene que ser JSON valido (comillas dobles, sin comas colgando). Usá
   `null` para un numero que no pudiste leer, nunca un cero.

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
  "noticias": [ { "bloque": "Argentina", "titulo": "", "detalle": "",
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

   (Los numeros de arriba son de ejemplo del formato, no datos.)

3. Validá el JSON antes de publicar:
   `python -c "import json,re,sys;s=open(sys.argv[1],encoding='utf-8').read();json.loads(re.search(r'id=\"datos\">(.*?)</script>',s,re.S).group(1));print('ok')" <ARCHIVO>`

## 6. Publicar

La pagina tiene link fijo: Tobias la abre siempre desde el mismo lugar.

- Si existe `scripts/ggal_semanal_url.txt`, tiene la URL. Primero
  `Artifact` con `action: "read"` y esa `url` (sin eso el publish se rechaza),
  despues `Artifact` publish con `file_path` = el ARCHIVO DE SALIDA (ruta
  absoluta) y `url` = esa URL, sin `icon`, con `description` =
  "Reporte semanal de GGAL: la semana en numeros, noticias macro y panorama".
- Si no existe (primera vez): publish sin `url`, con `icon: "chart"` y la misma
  `description`, y guardá la URL que devuelve en `scripts/ggal_semanal_url.txt`
  (una linea, sin nada mas).
- Si el publish falla, no reintentes en loop: dejá el archivo commiteado y anotá
  el error al final de tu respuesta.

## 7. Commitear

- `git add` del ARCHIVO DE SALIDA (y de `scripts/ggal_semanal_url.txt` si lo
  creaste). Nunca `git add -A`.
- Commit `reporte semanal GGAL <semana>` y `git push origin master`.
- Si el push falla, no reintentes en loop.

Terminá con una respuesta corta: el link de la pagina y 3 lineas de resumen.
No es asesoramiento financiero: describí, no des ordenes.
