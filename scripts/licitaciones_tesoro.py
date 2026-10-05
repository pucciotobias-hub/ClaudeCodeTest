"""Fechas de las licitaciones del Tesoro, del cronograma oficial de Finanzas.

El cronograma es un PDF con un calendario por mes donde las fechas estan
marcadas solo con color (celeste = llamado, verde = licitacion, naranja =
liquidacion): leido como texto no dice nada, y WebFetch no lo abre. Aca se
cruza el color de cada celda con el numero que tiene adentro.

Uso:
    python scripts/licitaciones_tesoro.py            # proximas desde hoy
    python scripts/licitaciones_tesoro.py 2026-10    # un mes
    python scripts/licitaciones_tesoro.py todo       # el año entero

Si la URL del PDF cambia, sale de
https://www.argentina.gob.ar/economia/finanzas/licitaciones-de-letras-y-bonos-del-tesoro/cronograma-<AÑO>
"""
import datetime
import sys
import urllib.request

import fitz  # PyMuPDF

URL = "https://www.argentina.gob.ar/sites/default/files/calendario_prensa_0.pdf"
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
LEYENDA = ["Llamado", "Licitación", "Liquidación"]
DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


def color(fill):
    return tuple(round(x, 2) for x in fill)


def leer(pdf_bytes):
    """Devuelve (año, {(mes, dia): tipo})."""
    pagina = fitz.open(stream=pdf_bytes, filetype="pdf")[0]
    palabras = pagina.get_text("words")
    rellenos = [(d["rect"], color(d["fill"])) for d in pagina.get_drawings() if d.get("fill")]

    año = next(int(w[4]) for w in palabras if w[4].isdigit() and len(w[4]) == 4)

    # Color de cada tipo: la celda coloreada pegada a la izquierda del rotulo.
    tipos = {}
    for nombre in LEYENDA:
        r = pagina.search_for(nombre)[0]
        medio = (r.y0 + r.y1) / 2
        celdas = [(r.x0 - c.x1, col) for c, col in rellenos
                  if c.y0 <= medio <= c.y1 and c.x1 <= r.x0 + 1 and col != (1.0, 1.0, 1.0)]
        tipos[min(celdas)[1]] = nombre.lower()
    if len(tipos) != 3:
        raise SystemExit("No pude leer la leyenda de colores: cambio el formato del PDF.")

    # Los titulos van centrados sobre cada grilla. "Mayo" aparece tambien en la
    # nota del feriado del 25/05: de las repeticiones se queda la que esta
    # alineada con los titulos de los meses que salen una sola vez.
    halladas = {mes: pagina.search_for(mes) for mes in MESES}
    centros = [(r[0].x0 + r[0].x1) / 2 for r in halladas.values() if len(r) == 1]
    titulos = []
    for i, mes in enumerate(MESES):
        if not halladas[mes] or not centros:
            raise SystemExit(f"No encontre el mes {mes}: cambio el formato del PDF.")
        r = min(halladas[mes], key=lambda r: min(abs((r.x0 + r.x1) / 2 - c) for c in centros))
        titulos.append((i + 1, r))
    corte_x = pagina.rect.width / 2

    def mes_de(x, y):
        # El titulo del mes esta arriba de su grilla: el ultimo titulo de esa
        # columna que quede por encima de la celda.
        arriba = [(t.y0, m) for m, t in titulos if (t.x0 < corte_x) == (x < corte_x) and t.y0 <= y]
        return max(arriba)[1] if arriba else None

    fechas = {}
    for celda, col in rellenos:
        if col not in tipos or celda.y0 < 110:  # 110: debajo de la leyenda
            continue
        adentro = [w[4] for w in palabras
                   if celda.x0 <= (w[0] + w[2]) / 2 <= celda.x1
                   and celda.y0 <= (w[1] + w[3]) / 2 <= celda.y1 and w[4].isdigit()]
        mes = mes_de((celda.x0 + celda.x1) / 2, celda.y0)
        if len(adentro) == 1 and mes:
            fechas[(mes, int(adentro[0]))] = tipos[col]
    return año, fechas


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    año, fechas = leer(urllib.request.urlopen(req, timeout=30).read())

    filas = sorted((datetime.date(año, m, d), t) for (m, d), t in fechas.items())
    n = sum(1 for _, t in filas if t == "licitación")
    if n < 12:
        raise SystemExit(f"Solo lei {n} licitaciones en el año: cambio el formato del PDF.")

    if arg == "todo":
        pass
    elif arg:
        filas = [f for f in filas if f[0].strftime("%Y-%m") == arg]
    else:
        hoy = datetime.date.today()
        filas = [f for f in filas if f[0] >= hoy][:9]

    print(f"Cronograma de licitaciones {año} (Secretaria de Finanzas) - {URL}")
    for fecha, tipo in filas:
        print(f"{fecha.isoformat()} {DIAS[fecha.weekday()]}  {tipo}")
    if not filas:
        print("(sin fechas en ese rango)")


if __name__ == "__main__":
    main()
