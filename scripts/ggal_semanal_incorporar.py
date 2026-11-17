"""Mete el JSON de la semana adentro de la pagina del reporte semanal.

La pagina (scripts/ggal_semanal_pagina.html) muestra la semana que trae
incorporada en su bloque <script id="datos">: una pagina publicada no puede
leer un documento de Claude Docs (falla con self_only para cualquier visor),
asi que cada semana se reemplaza ese bloque y se republica.

Uso:
    py scripts/ggal_semanal_incorporar.py estudios/ggal/semanal/<FECHA>.json
"""
import json
import pathlib
import sys

PAGINA = pathlib.Path(__file__).with_name("ggal_semanal_pagina.html")
ABRE = '<script type="application/json" id="datos">'


def main():
    datos = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    if not (datos.get("semana") and datos.get("ggal")):
        raise SystemExit("El JSON no trae 'semana' y 'ggal': no se toca la pagina.")
    # Una semana sin cierre es una corrida sin feed: la pagina quedaba sin precio
    # y sin grafico y parecia actualizada (paso el 19-oct).
    if datos["ggal"].get("cierre") is None:
        raise SystemExit("El JSON no trae el cierre de GGAL (corrida sin feed?): no se toca la pagina.")
    # El 16-nov las velas vinieron como el texto "__VELAS__": len() daba 9 y pasaba el
    # control viejo, y la pagina salio sin grafico. Se exige una lista de filas de 6.
    velas = datos.get("velas")
    if not (isinstance(velas, list) and len(velas) >= 6
            and all(isinstance(v, list) and len(v) == 6 for v in velas)):
        raise SystemExit("Las 'velas' no son una lista de filas [fecha, a, M, m, c, vol]: "
                         "correr antes scripts/ggal_semanal_velas.py. No se toca la pagina.")
    # "</" cerraria el <script> si apareciera en un texto.
    bloque = json.dumps(datos, ensure_ascii=False, indent=1).replace("</", "<\\/")

    html = PAGINA.read_text(encoding="utf-8")
    desde = html.index(ABRE) + len(ABRE)
    hasta = html.index("</script>", desde)
    PAGINA.write_text(html[:desde] + "\n" + bloque + "\n" + html[hasta:], encoding="utf-8", newline="\n")
    print(f"ok: pagina con la semana {datos['semana']}")


if __name__ == "__main__":
    main()
