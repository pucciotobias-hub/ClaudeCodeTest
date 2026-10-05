"""Mete el JSON de la semana adentro de la pagina del reporte semanal.

La pagina (scripts/ggal_semanal_pagina.html) muestra la semana que trae
incorporada en su bloque <script id="datos">: una pagina publicada no puede
leer un documento de Claude Docs (falla con self_only para cualquier visor),
asi que cada semana se reemplaza ese bloque y se republica.

Uso:
    python scripts/ggal_semanal_incorporar.py estudios/ggal/semanal/<FECHA>.json
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
    # "</" cerraria el <script> si apareciera en un texto.
    bloque = json.dumps(datos, ensure_ascii=False, indent=1).replace("</", "<\\/")

    html = PAGINA.read_text(encoding="utf-8")
    desde = html.index(ABRE) + len(ABRE)
    hasta = html.index("</script>", desde)
    PAGINA.write_text(html[:desde] + "\n" + bloque + "\n" + html[hasta:], encoding="utf-8", newline="\n")
    print(f"ok: pagina con la semana {datos['semana']}")


if __name__ == "__main__":
    main()
