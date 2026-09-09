# -*- coding: utf-8 -*-
"""
Genera el PDF "Estados Contables FRESIA S.A.A.G. 2026" con formato uniforme.

Flujo:
  1. Carga los datos extraidos del PDF original (data.py, importes como texto).
  2. Valida los puntos de control contables (assertions.py). Si alguno falla,
     ABORTA y no genera nada.
  3. Arma el HTML aplicando el sistema de diseño (styles.css).
  4. Exporta a PDF con WeasyPrint.

En ningun punto del flujo se convierte un importe a numero. Los importes viajan
como cadenas desde data.py hasta el HTML final.

Uso:
    python build.py [-o salida.pdf] [--html]
"""
from __future__ import annotations

import argparse
import html as _html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data as D
from assertions import verificar_puntos_de_control

AQUI = os.path.dirname(os.path.abspath(__file__))

# Orden de paginas aprobado: Anexos I-VII, luego los estados basicos, luego notas.
# Para volver al orden del PDF original (anexos, EFE, ER, EPN, ESP, notas)
# cambiar ORDEN_ESTADOS por "original".
ORDEN_ESTADOS = "estandar"   # "estandar" | "original"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def esc(t: str) -> str:
    """Escapa el texto pero respeta las etiquetas <br> y las entidades &nbsp;."""
    t = _html.escape(t, quote=False)
    return t.replace("&lt;br&gt;", "<br>").replace("&amp;nbsp;", "&nbsp;")


def n_columnas(spec) -> int:
    """Cantidad total de columnas del cuadro = 1 concepto + N columnas de datos."""
    ancho = 0
    for _, _, vals in spec["rows"]:
        ancho = max(ancho, len(vals))
    return ancho + 1


def colgroup(spec, ncols: int) -> str:
    concept_w = spec.get("concept_width", "30%")
    resto = (100.0 - float(concept_w.rstrip("%"))) / (ncols - 1)
    cols = [f'<col style="width:{concept_w}">']
    cols += [f'<col style="width:{resto:.4f}%">'] * (ncols - 1)
    return "<colgroup>" + "".join(cols) + "</colgroup>"


def thead(spec, ncols: int) -> str:
    filas = []
    for fila in spec["head"]:
        celdas = []
        for cell in fila:
            texto, colspan, cls = cell[0], cell[1], cell[2]
            rowspan = cell[3] if len(cell) > 3 else 1
            attrs = f' class="{cls}"'
            if colspan > 1:
                attrs += f' colspan="{colspan}"'
            if rowspan > 1:
                attrs += f' rowspan="{rowspan}"'
            celdas.append(f"<th{attrs}>{esc(texto)}</th>")
        filas.append("<tr>" + "".join(celdas) + "</tr>")
    return "<thead>" + "".join(filas) + "</thead>"


def tbody(spec, ncols: int, rows=None) -> str:
    ndatos = ncols - 1
    filas = []
    for kind, concepto, vals in (spec["rows"] if rows is None else rows):
        vals = list(vals) + [""] * (ndatos - len(vals))
        clase = {
            "head": "r-head", "data": "r-data", "data-i": "r-data-i",
            "total": "r-total", "spacer": "r-spacer", "grand": "r-grand",
            "label": "r-label",
        }[kind]
        celdas = [f'<td class="concepto">{esc(concepto)}</td>']
        for i, v in enumerate(vals):
            # En Anexo II la segunda columna ("Clase") va centrada.
            cls = "cls" if (spec.get("col_centrada") == i) else "num"
            celdas.append(f'<td class="{cls}">{esc(v)}</td>')
        filas.append(f'<tr class="{clase}">' + "".join(celdas) + "</tr>")
    return "<tbody>" + "".join(filas) + "</tbody>"


def bloque_firmas() -> str:
    nombres = "".join(f'<td class="nombre">{esc(n)}</td>' for n, _ in D.FIRMAS)
    cargos = "".join(f"<td>{esc(c)}</td>" for _, c in D.FIRMAS)
    return (f'<table class="firmas"><tr>{nombres}</tr><tr>{cargos}</tr></table>')


def bloque_pie(notas_pie) -> str:
    extra = ""
    if notas_pie:
        ps = "".join(f"<p>{esc(t)}</p>" for t in notas_pie)
        extra = f'<div class="notas-anexo">{ps}</div>'
    return (f'<div class="pie"><div>{esc(D.PIE_NOTAS)}</div>'
            f"<div>{esc(D.PIE_DICTAMEN)}</div>{extra}</div>")


def cabecera(spec) -> str:
    tag = spec.get("anexo")
    if tag:
        tag_html = f'<div class="tag-anexo">{esc(tag)}</div>'
    else:
        tag_html = '<div class="tag-anexo vacio">&nbsp;</div>'
    return tag_html + f'<div class="caja-empresa">{esc(D.EMPRESA)}</div>'


def titulo_bloque(spec, sufijo: str = "") -> str:
    chico = " chico" if len(spec["titulo"]) > 42 else ""
    sub = spec["subtitulo"] + sufijo
    return (f'<div class="titulo{chico}">{esc(spec["titulo"])}</div>'
            f'<div class="subtitulo">{esc(sub)}</div>')


# --------------------------------------------------------------------------
# Paginas de cuadro (apaisadas)
# --------------------------------------------------------------------------
def pagina_cuadro(spec, rows=None, sufijo: str = "", notas_pie=None) -> str:
    ncols = n_columnas(spec)
    tabla = (f'<table class="cuadro">{colgroup(spec, ncols)}'
             f"{thead(spec, ncols)}{tbody(spec, ncols, rows)}</table>")
    if notas_pie is None:
        notas_pie = spec.get("notas_pie", [])
    return (
        '<section class="hoja apaisada">'
        + cabecera(spec)
        + '<div class="marco">' + titulo_bloque(spec, sufijo) + tabla + "</div>"
        + bloque_pie(notas_pie)
        + bloque_firmas()
        + "</section>"
    )


def paginas_cuadro(spec):
    """Devuelve una o mas paginas. Si el cuadro no entra en una hoja A4 apaisada
    a 7,6 pt, se parte en hojas del MISMO formato repitiendo integramente el
    encabezado de columnas, sin achicar la fuente ni el ancho del cuadro."""
    corte = spec.get("partir_en")
    if not corte:
        return [pagina_cuadro(spec)]
    filas = spec["rows"]
    trozos = [filas[:corte], filas[corte:]]
    n = len(trozos)
    paginas = []
    for i, trozo in enumerate(trozos):
        if i == 0:
            sufijo = f"  (Continúa en hoja {i + 2} de {n})"
        else:
            sufijo = f"  (Continuación - hoja {i + 1} de {n})"
        paginas.append(pagina_cuadro(spec, rows=trozo, sufijo=sufijo,
                                     notas_pie=spec.get("notas_pie", []) if i == n - 1 else []))
    return paginas


def pagina_esp() -> str:
    """Estado de Situacion Patrimonial: dos paneles (Activos | Pasivos)."""
    izq, der = D.ESP["izq"], D.ESP["der"]
    n = max(len(izq), len(der))
    izq = izq + [("spacer", "", [])] * (n - len(izq))
    der = der + [("spacer", "", [])] * (n - len(der))

    clase = {"head": "r-head", "data": "r-data", "total": "r-total", "spacer": "r-spacer"}
    filas = []
    for (ki, ci, vi), (kd, cd, vd) in zip(izq, der):
        vi = list(vi) + [""] * (2 - len(vi))
        vd = list(vd) + [""] * (2 - len(vd))
        # La clase de fila se toma del panel izquierdo; el panel derecho
        # lleva su propia clase en cada celda.
        ci_cls = clase[ki]
        cd_cls = clase[kd]
        peso_i = "font-weight:bold" if ki in ("head", "total") else ""
        peso_d = "font-weight:bold" if kd in ("head", "total") else ""
        borde_i = "border-top:1pt solid #000;border-bottom:1pt solid #000" if ki == "total" else ""
        borde_d = "border-top:1pt solid #000;border-bottom:1pt solid #000" if kd == "total" else ""
        si = ";".join(x for x in (peso_i, borde_i) if x)
        sd = ";".join(x for x in (peso_d, borde_d) if x)
        st_i = f' style="{si}"' if si else ""
        st_d = f' style="{sd}"' if sd else ""
        celdas = [f'<td class="concepto"{st_i}>{esc(ci)}</td>']
        celdas += [f'<td class="num"{st_i}>{esc(v)}</td>' for v in vi]
        celdas += [f'<td class="concepto"{st_d}>{esc(cd)}</td>']
        celdas += [f'<td class="num"{st_d}>{esc(v)}</td>' for v in vd]
        cls_fila = "r-spacer" if (ki == "spacer" and kd == "spacer") else "r-data"
        filas.append(f'<tr class="{cls_fila}">' + "".join(celdas) + "</tr>")

    cg = ('<colgroup><col style="width:25%"><col style="width:12.5%"><col style="width:12.5%">'
          '<col style="width:25%"><col style="width:12.5%"><col style="width:12.5%"></colgroup>')
    th = ('<thead><tr><th class="concepto"></th><th class="num">2026</th><th class="num">2025</th>'
          '<th class="concepto"></th><th class="num">2026</th><th class="num">2025</th></tr></thead>')
    tabla = f'<table class="cuadro">{cg}{th}<tbody>' + "".join(filas) + "</tbody></table>"

    spec = D.ESP
    return (
        '<section class="hoja apaisada">'
        + cabecera(spec)
        + '<div class="marco">' + titulo_bloque(spec) + tabla + "</div>"
        + bloque_pie([])
        + bloque_firmas()
        + "</section>"
    )


# --------------------------------------------------------------------------
# Paginas de notas (verticales)
# --------------------------------------------------------------------------
def cuadro_nota(titulo, filas, total) -> str:
    cg = ('<colgroup><col style="width:56%"><col style="width:22%">'
          '<col style="width:22%"></colgroup>')
    th = ('<thead><tr><th class="concepto"></th><th class="num">31-ene-26</th>'
          '<th class="num">31-ene-25</th></tr></thead>')
    cuerpo = []
    for concepto, v26, v25 in filas:
        if concepto.startswith("__label__"):
            cuerpo.append(
                '<tr class="r-label"><td class="concepto">'
                + esc(concepto.replace("__label__", ""))
                + '</td><td class="num"></td><td class="num"></td></tr>')
            continue
        cuerpo.append('<tr class="r-data"><td class="concepto">' + esc(concepto)
                      + f'</td><td class="num">{esc(v26)}</td>'
                      + f'<td class="num">{esc(v25)}</td></tr>')
    tl, t26, t25 = total
    cuerpo.append('<tr class="r-grand"><td class="concepto">' + esc(tl)
                  + f'</td><td class="num">{esc(t26)}</td>'
                  + f'<td class="num">{esc(t25)}</td></tr>')
    tabla = (f'<table class="cuadro notas">{cg}{th}<tbody>'
             + "".join(cuerpo) + "</tbody></table>")
    return ('<div class="n-cuadro-bloque">'
            f'<div class="n-cuadro-titulo">{esc(titulo)}</div>{tabla}</div>')


def paginas_notas() -> str:
    """Las notas van en un unico flujo continuo: WeasyPrint las pagina solo.
    Cada cuadro lleva page-break-inside:avoid, de modo que ningun cuadro queda
    partido entre dos hojas, pero tampoco quedan hojas a medio llenar."""
    p = ['<section class="hoja vertical">']

    p.append('<div class="notas-titulo-bloque">')
    p.append(f'<div class="caja-empresa">{esc(D.EMPRESA)}</div>')
    p.append('<div class="titulo">NOTAS A LOS ESTADOS CONTABLES</div>')
    p.append(f'<div class="subtitulo">{esc(D.SUB_COMP)}</div>')
    p.append("</div>")

    for kind, txt in D.NOTA_1_PARRAFOS:
        cls = {"h1": "n-h1", "h2": "n-h2", "p": "n-p", "li": "n-li"}[kind]
        p.append(f'<div class="{cls}">{esc(txt)}</div>')

    # Cuadros de composicion de rubros (2.1 a 2.12)
    for titulo, filas, total in D.NOTAS_CUADROS:
        p.append(cuadro_nota(titulo, filas, total))
        if titulo.startswith("2.10."):
            p.append(f'<div class="n-remision">{esc(D.NOTA_210_REMISION)}</div>')

    # Notas de remision 2.13 a 2.15
    for t, txt in D.NOTAS_REMISION:
        p.append('<div class="n-bloque-corto">'
                 f'<div class="n-cuadro-titulo">{esc(t)}</div>'
                 f'<div class="n-remision">{esc(txt)}</div></div>')

    # Notas 3 a 5
    for titulo, filas, total in D.NOTAS_FINALES:
        p.append(cuadro_nota(titulo, filas, total))

    # Nota 6
    t6, txt6 = D.NOTA_6
    p.append('<div class="n-bloque-corto">'
             f'<div class="n-cuadro-titulo">{esc(t6)}</div>'
             f'<div class="n-remision">{esc(txt6)}</div></div>')

    p.append(bloque_firmas())
    p.append("</section>")
    return "".join(p)


# --------------------------------------------------------------------------
# Documento completo
# --------------------------------------------------------------------------
def construir_html() -> str:
    anexos = [D.ANEXO_I, D.ANEXO_II, D.ANEXO_III, D.ANEXO_IV,
              D.ANEXO_V, D.ANEXO_VI, D.ANEXO_VII]
    D.ANEXO_II["col_centrada"] = 0   # columna "Clase"

    paginas = []
    for a in anexos:
        paginas.extend(paginas_cuadro(a))

    if ORDEN_ESTADOS == "estandar":
        paginas.append(pagina_esp())
        paginas.extend(paginas_cuadro(D.ER))
        paginas.extend(paginas_cuadro(D.EPN))
        paginas.extend(paginas_cuadro(D.EFE))
    else:
        paginas.extend(paginas_cuadro(D.EFE))
        paginas.extend(paginas_cuadro(D.ER))
        paginas.extend(paginas_cuadro(D.EPN))
        paginas.append(pagina_esp())

    paginas.append(paginas_notas())

    with open(os.path.join(AQUI, "styles.css"), encoding="utf-8") as f:
        css = f.read()

    return (
        "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
        "<title>FRESIA S.A. A.G. - Estados Contables 2026</title>"
        f"<style>{css}</style></head><body>"
        + "".join(paginas)
        + "</body></html>"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output",
                    default=os.path.join(AQUI, "Fresia_SAAG_Estados_Contables_2026.pdf"))
    ap.add_argument("--html", action="store_true", help="guardar tambien el HTML intermedio")
    args = ap.parse_args()

    print("1) Validando puntos de control contables...")
    ok, detalle = verificar_puntos_de_control()
    for linea in detalle:
        print("   " + linea)
    if not ok:
        print("\nABORTADO: los puntos de control no coinciden. No se genero ningun PDF.")
        return 1

    print("2) Armando HTML...")
    doc = construir_html()
    if args.html:
        ruta_html = os.path.splitext(args.output)[0] + ".html"
        with open(ruta_html, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"   HTML -> {ruta_html}")

    print("3) Generando PDF con WeasyPrint...")
    from weasyprint import HTML
    HTML(string=doc, base_url=AQUI).write_pdf(args.output)
    print(f"   PDF  -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
