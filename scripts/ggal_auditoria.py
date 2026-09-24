"""Auditoria de los estudios de GGAL: contrasta los mapas de niveles contra lo que hizo el precio.

Es la parte objetiva de la auditoria. Lee los informes de estudios/ggal/, toma las
barras diarias que le pasa el agente (volcadas del chart de TradingView, el mismo
feed BATS con el que se escribieron los estudios) y mide tres cosas:

  1. Niveles: cada nivel del mapa, en las N ruedas siguientes al estudio, fue
     respetado, perforado y recuperado, roto o no se testeo.
  2. Extremos anticipados: que porcentaje de los maximos y minimos diarios cayo
     sobre un nivel del mapa vigente, contra una grilla pareja de niveles.
  3. Datos del encabezado: el OHLC que reporta cada informe de cierre contra la
     barra real.

Lo cualitativo (escenarios, sesgo, lectura macro) lo evalua el agente leyendo los
informes; este script no lo intenta.

Uso:
    python scripts/ggal_auditoria.py --barras barras.json [--desde 2026-09-14]
        [--hasta 2026-09-18] [--horizonte 3] [--tol-pct 0.25]

El JSON de barras es {"bars": [["YYYY-MM-DD", o, h, l, c, v], ...]} con barras
diarias en orden cronologico. --hasta es la ultima rueda COMPLETA: si se corre
con el mercado abierto, hay que pasarla para dejar afuera la vela en curso.
"""
import argparse
import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

RE_ARCHIVO = re.compile(r"^(\d{4}-\d{2}-\d{2})-(apertura|cierre)\.md$")
RE_NIVEL = re.compile(r"^\|\s*\**(R\d+|S\d+|PIVOTE)\**\s*\|\s*\**([\d.]+)\**\s*\|")
RE_PRECIO = re.compile(r"\*\*Precio\*\*\s*([\d.]+)")
RE_DIA = re.compile(
    r"\*\*D[ií]a\*\*\s*O\s*([\d.]+)\s*/\s*H\s*([\d.]+)\s*/\s*L\s*([\d.]+)\s*/\s*C\s*([\d.]+)"
)


@dataclass
class Estudio:
    fecha: str
    turno: str
    archivo: str
    precio: float | None
    dia: tuple[float, float, float, float] | None
    niveles: list[tuple[str, float]] = field(default_factory=list)
    # Indice de la primera barra que el estudio NO vio. Se calcula despues.
    inicio: int | None = None

    @property
    def nombre(self) -> str:
        return f"{self.fecha} {self.turno}"


def cargar_estudios(carpeta: Path) -> list[Estudio]:
    estudios = []
    for f in sorted(carpeta.glob("*.md")):
        m = RE_ARCHIVO.match(f.name)
        if not m:
            continue
        texto = f.read_text(encoding="utf-8")
        precio = RE_PRECIO.search(texto)
        dia = RE_DIA.search(texto)
        niveles = [(g.group(1), float(g.group(2))) for g in map(RE_NIVEL.match, texto.splitlines()) if g]
        estudios.append(
            Estudio(
                fecha=m.group(1),
                turno=m.group(2),
                archivo=f.name,
                precio=float(precio.group(1)) if precio else None,
                dia=tuple(float(x) for x in dia.groups()) if dia else None,
                niveles=niveles,
            )
        )
    # Mismo dia: la apertura va antes que el cierre.
    estudios.sort(key=lambda e: (e.fecha, e.turno != "apertura"))
    return estudios


def ubicar(estudios: list[Estudio], fechas: list[str]) -> None:
    """Marca desde que barra empieza lo que cada estudio no pudo ver.

    Un cierre ya vio la vela de su dia. Una apertura en pre-mercado no, pero
    varias corrieron tarde y leyeron parte de la vela (encabezado con O/H/L/C en
    vez de N/D). En ese caso se la trata como si hubiera visto el dia entero: es
    conservador, pero evita darle por acertado un nivel que dibujo sobre un minimo
    que ya habia pasado.
    """
    for e in estudios:
        vio_el_dia = e.turno == "cierre" or e.dia is not None
        e.inicio = next(
            (i for i, f in enumerate(fechas) if (f > e.fecha if vio_el_dia else f >= e.fecha)),
            len(fechas),
        )


def evaluar_nivel(nivel: float, ref: float, barras: list, tol: float) -> tuple[str, str | None, float]:
    """Primer contacto del precio con el nivel dentro de la ventana.

    Devuelve (resultado, fecha, exceso), donde exceso es cuanto paso el intradia
    del otro lado del nivel, en % (0 si no lo paso). Resultados:
      'respetado'  toco y el intradia no lo paso mas alla de la tolerancia
      'perforado'  lo paso en el intradia pero cerro del lado original
      'roto'       cerro del otro lado
      'roto (gap)' lo salto entero con un gap
      'sin test'   nunca llego
    """
    soporte = nivel < ref
    for fecha, _o, h, l, c, _v in barras:
        if soporte and h < nivel - tol or not soporte and l > nivel + tol:
            return "roto (gap)", fecha, 0.0
        if l <= nivel + tol and h >= nivel - tol:
            exceso = max(0.0, (nivel - l) if soporte else (h - nivel)) / nivel * 100
            if c < nivel - tol if soporte else c > nivel + tol:
                return "roto", fecha, exceso
            return ("perforado" if exceso > tol / nivel * 100 else "respetado"), fecha, exceso
    return "sin test", None, 0.0


def cobertura(dias: list[tuple[list[float], float, float]], tol_pct: float) -> tuple[int, int, float]:
    """Cuantos extremos diarios cayeron a tol_pct de un nivel, y lo que daria una grilla.

    La grilla es la referencia: la misma cantidad de niveles repartidos parejo en el
    rango del mapa. Si el mapa no le gana, los niveles no estan marcando giros.
    """
    aciertos, total, bases = 0, 0, []
    for precios, h, l in dias:
        for extremo in (h, l):
            total += 1
            aciertos += min(abs(n - extremo) for n in precios) / extremo * 100 <= tol_pct
        rango = max(precios) - min(precios)
        if rango > 0:
            bases.append(min(1.0, len(precios) * 2 * tol_pct / 100 * statistics.mean(precios) / rango))
    return aciertos, total, statistics.mean(bases) if bases else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--barras", required=True, type=Path)
    ap.add_argument("--estudios", type=Path, default=Path(__file__).resolve().parent.parent / "estudios" / "ggal")
    ap.add_argument("--desde", help="primer estudio a auditar (YYYY-MM-DD). Default: todos")
    ap.add_argument("--hasta", help="ultima rueda completa (YYYY-MM-DD). Default: la ultima barra")
    ap.add_argument("--horizonte", type=int, default=3, help="ruedas que se le dan a cada mapa (default 3)")
    ap.add_argument("--tol-pct", type=float, default=0.25, help="tolerancia de contacto en %% del nivel (default 0.25)")
    args = ap.parse_args()

    datos = json.loads(args.barras.read_text(encoding="utf-8"))
    barras = [b for b in datos["bars"] if not args.hasta or b[0] <= args.hasta]
    if not barras:
        print("No hay barras.", file=sys.stderr)
        return 1
    fechas = [b[0] for b in barras]
    por_fecha = {b[0]: b for b in barras}

    estudios = cargar_estudios(args.estudios)
    ubicar(estudios, fechas)
    auditados = [e for e in estudios if not args.desde or e.fecha >= args.desde]

    out = []
    p = out.append
    p(f"# Auditoria objetiva — estudios {auditados[0].fecha if auditados else '-'} a "
      f"{auditados[-1].fecha if auditados else '-'}")
    p("")
    p(f"Barras: {datos.get('sym', '?')} diario, {fechas[0]} a {fechas[-1]}. "
      f"Horizonte {args.horizonte} ruedas, tolerancia {args.tol_pct}% del nivel.")
    p("")

    # --- 1. Niveles --------------------------------------------------------
    p("## 1. Niveles: que paso en las ruedas siguientes")
    p("")
    eventos = {}  # (nivel, fecha de contacto) -> resultado, para no contar dos veces el mismo toque
    ventanas_incompletas = []
    for e in auditados:
        if not e.niveles or e.precio is None:
            p(f"- **{e.nombre}**: sin tabla de niveles o sin precio, no se evalua.")
            continue
        ventana = barras[e.inicio:e.inicio + args.horizonte]
        completa = len(ventana) == args.horizonte
        if not completa:
            ventanas_incompletas.append(f"{e.nombre} ({len(ventana)}/{args.horizonte})")
        p(f"### {e.nombre} — ref {e.precio:.2f}, ventana "
          f"{ventana[0][0] + ' a ' + ventana[-1][0] if ventana else 'vacia'}"
          f"{'' if completa else ' (INCOMPLETA)'}")
        p("")
        p("| | Nivel | Rol | Resultado | Rueda |")
        p("|---|---|---|---|---|")
        for etiqueta, nivel in e.niveles:
            tol = nivel * args.tol_pct / 100
            if abs(nivel - e.precio) <= tol:
                p(f"| {etiqueta} | {nivel:.2f} | en precio | no se evalua | |")
                continue
            rol = "soporte" if nivel < e.precio else "resistencia"
            res, fecha, exceso = evaluar_nivel(nivel, e.precio, ventana, tol)
            aviso = ""
            if (etiqueta.startswith("S") and rol == "resistencia") or (etiqueta.startswith("R") and rol == "soporte"):
                aviso = f" (etiquetado {etiqueta[0]})"
            detalle = f" por {exceso:.2f}%" if res == "perforado" else ""
            p(f"| {etiqueta} | {nivel:.2f} | {rol}{aviso} | {res}{detalle} | {fecha or ''} |")
            if fecha and completa:
                eventos.setdefault((round(nivel, 2), fecha), (res, rol, exceso))
        p("")

    conteo = {"respetado": 0, "perforado": 0, "roto": 0, "roto (gap)": 0}
    for res, _rol, _ in eventos.values():
        conteo[res] += 1
    tocados = sum(conteo.values())
    aguanto = conteo["respetado"] + conteo["perforado"]
    p("**Resumen de niveles** (toques unicos: el mismo nivel tocado el mismo dia cuenta una vez "
      "aunque figure en varios mapas; solo ventanas completas)")
    p("")
    if tocados:
        p(f"- Aguantaron al cierre: **{aguanto}/{tocados}** ({100 * aguanto / tocados:.0f}%) — "
          f"{conteo['respetado']} limpios, {conteo['perforado']} perforados en el intradia y recuperados")
        excesos = sorted(x for r, _, x in eventos.values() if r == "perforado")
        if excesos:
            p(f"- Perforacion de los que aguantaron: mediana **{statistics.median(excesos):.2f}%**, "
              f"maxima {excesos[-1]:.2f}% (a 40 USD, 0,5% son 20 centavos)")
        p(f"- Rotos: {conteo['roto']} al cierre, {conteo['roto (gap)']} con gap")
        for rol in ("soporte", "resistencia"):
            sub = [r for r, ro, _ in eventos.values() if ro == rol]
            if sub:
                ok = sum(r in ("respetado", "perforado") for r in sub)
                p(f"- Como {rol}: {ok}/{len(sub)} aguantaron")
    else:
        p("- Sin toques en ventanas completas.")
    if ventanas_incompletas:
        p(f"- Ventanas incompletas (fuera del resumen): {', '.join(ventanas_incompletas)}")
    p("")

    # --- 2. Extremos anticipados ------------------------------------------
    p("## 2. Extremos anticipados: el maximo y el minimo de cada rueda, contra el mapa vigente")
    p("")
    p("Mapa vigente = el ultimo estudio que se escribio sin ver esa rueda. La referencia es una "
      "**grilla pareja**: la misma cantidad de niveles repartidos parejo en el rango del mapa.")
    p("")
    p("| Rueda | Mapa | Maximo | Nivel mas cerca | Minimo | Nivel mas cerca |")
    p("|---|---|---|---|---|---|")
    dias, distancias = [], []
    primera = min((e.inicio for e in auditados), default=len(barras))
    for i in range(primera, len(barras)):
        fecha, _o, h, l, _c, _v = barras[i]
        vigentes = [e for e in estudios if e.inicio <= i and e.niveles]
        if not vigentes:
            continue
        mapa = vigentes[-1]
        precios = [n for _, n in mapa.niveles]
        dias.append((precios, h, l))
        celdas = []
        for extremo in (h, l):
            cercano = min(precios, key=lambda n: abs(n - extremo))
            dist = abs(cercano - extremo) / extremo * 100
            distancias.append(dist)
            celdas += [f"{extremo:.2f}", f"{cercano:.2f} ({dist:.2f}%){' ✓' if dist <= args.tol_pct else ''}"]
        p(f"| {fecha} | {mapa.nombre} | " + " | ".join(celdas) + " |")
    p("")
    if dias:
        for tol in (args.tol_pct, 2 * args.tol_pct):
            ok, total, base = cobertura(dias, tol)
            p(f"- A {tol:g}%: **{ok}/{total}** extremos sobre un nivel ({100 * ok / total:.0f}%) · "
              f"grilla pareja ~{100 * base:.0f}%")
        p(f"- Distancia mediana del extremo al nivel mas cercano: {statistics.median(distancias):.2f}%")
        p(f"- Muestra: {len(dias)} ruedas. Con menos de ~40 la diferencia contra la grilla es ruido; "
          f"mirar la tendencia de varias auditorias, no un numero suelto.")
    p("")

    # --- 3. Datos del encabezado ------------------------------------------
    p("## 3. Datos del encabezado de los cierres contra la barra real")
    p("")
    errores = 0
    for e in auditados:
        if e.turno != "cierre" or not e.dia:
            continue
        barra = por_fecha.get(e.fecha)
        if not barra:
            p(f"- {e.nombre}: no hay barra para comparar.")
            continue
        difs = []
        for nombre, rep, real in zip("OHLC", e.dia, barra[1:5]):
            # Los informes redondean a 2 decimales y el feed trae hasta 4.
            if abs(rep - real) > 0.011:
                difs.append(f"{nombre} {rep} vs {real}")
        if difs:
            errores += 1
            p(f"- **{e.nombre}**: " + ", ".join(difs))
    if not errores:
        p("- Todos los encabezados de cierre coinciden con la barra (±0,01).")
    p("")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
