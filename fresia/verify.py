# -*- coding: utf-8 -*-
"""
Verificacion de fidelidad: compara los importes del PDF generado contra los del
PDF original, token por token.

- Todo importe que aparece en el PDF nuevo TIENE que existir en alguno de los
  PDF de origen (v21 como fuente principal, v14 para las notas al pie del
  Anexo II que se recuperaron).
- Se listan tambien los importes del original que no estan en el nuevo, para
  poder revisarlos a mano (los esperados son los artefactos de sobreimpresion
  del original, donde un valor viejo quedo pintado debajo de uno corregido).

Uso:  python verify.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter

import fitz

AQUI = os.path.dirname(os.path.abspath(__file__))

ORIGEN = r"C:\Users\Tobias\Downloads\Fresia_SAAG_Estados_Contables_2026_formato_uniforme_con_Anexo_II_FINAL_v21 (1).pdf"
ORIGEN_V14 = r"C:\Users\Tobias\Downloads\Fresia_SAAG_Estados_Contables_2026_formato_uniforme_con_Anexo_II_FINAL_v14.pdf"
NUEVO = os.path.join(AQUI, "Fresia_SAAG_Estados_Contables_2026.pdf")

# un importe: 1.234.567,89  /  1.234,56  /  123,45  /  0,00
IMPORTE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")

# Valores que estan en el PDF original pero NO deben estar en el nuevo.
# Son versiones viejas que en el original quedaron pintadas DEBAJO de un
# rectangulo blanco, con el valor corregido sobreimpreso encima. El extractor
# de texto las ve; el ojo no. Se toma el valor visible, que ademas coincide con
# los puntos de control de la consigna.
TAPADOS = {
    "191.257.782,19":     ("191.257.782,59", "EFE / EPN - Distribucion de resultados (punto de control)"),
    "2.247.002.837,42":   ("2.247.002.837,41", "Anexo VII - Ganado, existencias al inicio (punto de control)"),
    "2.912.477.360,28":   ("2.912.477.360,27", "Anexo VII - Total existencias al inicio (punto de control)"),
    "313.939.213,62":     ("313.939.213,22", "EFE - Flujo operativo (punto de control)"),
    "394.140.043,27":     ("394.140.043,28", "Anexo VII - Ganado VNR (punto de control)"),
    "510.874.975,06":     ("510.874.975,07", "Anexo VII - Total VNR (punto de control)"),
    "602.760.054,66":     ("602.760.054,26", "EFE - Aumento (Disminucion) de otras deudas (valor visible en el original)"),
}


def importes(ruta: str) -> Counter:
    d = fitz.open(ruta)
    txt = "\n".join(p.get_text() for p in d)
    d.close()
    return Counter(IMPORTE.findall(txt))


def main() -> int:
    if not os.path.exists(NUEVO):
        print("Todavia no existe el PDF generado. Corre primero build.py")
        return 1

    nuevo = importes(NUEVO)
    orig = importes(ORIGEN)
    orig14 = importes(ORIGEN_V14)
    disponibles = set(orig) | set(orig14)

    inventados = sorted(v for v in nuevo if v not in disponibles)
    faltantes = sorted(v for v in orig if v not in nuevo)

    print(f"Importes distintos en el PDF nuevo .... {len(nuevo)}")
    print(f"Importes distintos en el original ..... {len(orig)}")
    print()

    if inventados:
        print(f"!! {len(inventados)} importes del PDF nuevo NO estan en el original:")
        for v in inventados:
            print("   ", v)
    else:
        print("[OK] Ningun importe del PDF nuevo es ajeno al original.")

    print()
    esperados = [v for v in faltantes if v in TAPADOS]
    inesperados = [v for v in faltantes if v not in TAPADOS]

    if esperados:
        print(f"Importes del original ausentes del nuevo, TODOS explicados ({len(esperados)}):")
        for v in esperados:
            reemplazo, motivo = TAPADOS[v]
            marca = "OK " if reemplazo in nuevo else "!! "
            print(f"   [{marca}] {v}  ->  {reemplazo}   {motivo}")

    if inesperados:
        print()
        print(f"!! {len(inesperados)} importes del original DESAPARECIERON sin explicacion:")
        for v in inesperados:
            print("   ", v)
    elif not esperados:
        print("[OK] Todos los importes del original estan en el PDF nuevo.")

    faltan_reemplazos = [v for v in esperados if TAPADOS[v][0] not in nuevo]
    print()
    if not inventados and not inesperados and not faltan_reemplazos:
        print("RESULTADO: fidelidad verificada. Ningun importe inventado, alterado ni perdido.")
        return 0
    print("RESULTADO: HAY DIFERENCIAS QUE REVISAR.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
