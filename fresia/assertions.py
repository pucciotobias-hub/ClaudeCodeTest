# -*- coding: utf-8 -*-
"""
Puntos de control contables.

Este modulo NO calcula ni corrige nada: solo LEE las cadenas de data.py y
comprueba que sigan siendo exactamente las del PDF original. Si algo no
coincide, build.py aborta sin generar PDF.

La unica operacion aritmetica del modulo es la verificacion de la formula del
EPN pedida en la consigna, hecha con Decimal y en modo lectura: si el resultado
no da, se reporta el error; jamas se reescribe un importe.
"""
from __future__ import annotations

from decimal import Decimal

import data as D


def _a_decimal(s: str) -> Decimal:
    """Solo para VERIFICAR. El valor devuelto nunca vuelve al documento."""
    neg = s.strip().startswith("(")
    limpio = s.strip().strip("()").replace(".", "").replace(",", ".")
    d = Decimal(limpio)
    return -d if neg else d


def _fila(spec, etiqueta):
    for kind, concepto, vals in spec["rows"]:
        if concepto == etiqueta:
            return kind, concepto, vals
    return None


def verificar_puntos_de_control():
    errores, oks = [], []

    def chequear(nombre, obtenido, esperado):
        if obtenido == esperado:
            oks.append(f"[OK]    {nombre}: {esperado}")
        else:
            errores.append(f"[FALLA] {nombre}: esperado {esperado!r}, obtenido {obtenido!r}")

    # ---------------------------------------------------------------- ER
    f = _fila(D.ER, "RESULTADO ANTES IMPUESTO A LAS GANANCIAS")
    chequear("ER / Resultado antes de Impuesto a las Ganancias",
             f[2][0] if f else None, "460.334.551,09")

    # --------------------------------------------------------------- EPN
    ini = _fila(D.EPN, "Saldos al inicio")
    dis = _fila(D.EPN, "Distribución de resultados")
    res = _fila(D.EPN, "Resultado del ejercicio")
    cie = _fila(D.EPN, "SALDOS AL CIERRE DEL EJERCICIO")
    COL_PN = 7  # columna "TOTAL DEL PATRIMONIO NETO" (2026)

    chequear("EPN / PN al 31/01/2025 (saldo al inicio)", ini[2][COL_PN], "6.215.867.510,02")
    chequear("EPN / Distribucion de resultados",         dis[2][COL_PN], "(191.257.782,59)")
    chequear("EPN / Resultado del ejercicio",            res[2][COL_PN], "460.334.551,09")
    chequear("EPN / PN al cierre",                       cie[2][COL_PN], "6.484.944.278,52")

    # formula exacta pedida en la consigna (verificacion, no recalculo)
    suma = (_a_decimal(ini[2][COL_PN]) + _a_decimal(dis[2][COL_PN])
            + _a_decimal(res[2][COL_PN]))
    if suma == _a_decimal(cie[2][COL_PN]):
        oks.append("[OK]    EPN / formula 6.215.867.510,02 - 191.257.782,59 "
                   "+ 460.334.551,09 = 6.484.944.278,52")
    else:
        errores.append(f"[FALLA] EPN / la formula no cierra: da {suma}")

    # el PN del EPN debe ser el mismo del Estado de Situacion Patrimonial
    pn_esp = None
    for kind, concepto, vals in D.ESP["der"]:
        if concepto == "Según estado correspondiente":
            pn_esp = vals[0]
    chequear("ESP / Patrimonio Neto = PN del EPN", pn_esp, "6.484.944.278,52")

    # -------------------------------------------------------- ANEXO VII
    a7 = {c: v for _, c, v in D.ANEXO_VII["rows"]}
    chequear("Anexo VII / Total existencias al inicio",
             a7["Existencias al Inicio (actualizadas)"][3], "2.912.477.360,27")
    chequear("Anexo VII / Ganado, existencias al inicio",
             a7["Existencias al Inicio (actualizadas)"][2], "2.247.002.837,41")
    chequear("Anexo VII / Total VNR",
             a7["Resultado medición bienes de cambio a VNR"][3], "510.874.975,07")
    chequear("Anexo VII / Ganado VNR",
             a7["Resultado medición bienes de cambio a VNR"][2], "394.140.043,28")
    chequear("Anexo VII / Costo de ventas", a7["COSTO DE VENTAS"][3], "2.876.838.387,57")

    # -------------------------------------------------------------- EFE
    efe = {c: v for _, c, v in D.EFE["rows"]}
    chequear("EFE / Efectivo al inicio",
             efe["Efectivo al inicio del ejercicio (Notas 1.4.1.)"][0], "85.076.411,79")
    chequear("EFE / Efectivo al cierre",
             efe["Efectivo al cierre del ejercicio (Notas 1.4.1. y 2.1.)"][0], "98.557.263,73")
    chequear("EFE / Variacion neta del efectivo",
             efe["VARIACIÓN NETA DEL EFECTIVO"][0], "13.480.851,94")
    chequear("EFE / Depreciaciones",
             efe["Depreciación de bienes de uso"][0], "181.282.731,64")
    chequear("EFE / Flujo operativo",
             efe["FLUJO NETO DE EFECTIVO GENERADO POR LAS ACTIVIDADES OPERATIVAS"][0],
             "(313.939.213,22)")
    chequear("EFE / Flujo de inversion",
             efe["FLUJO NETO DE EFECTIVO APLICADO POR ACTIVIDADES DE INVERSIÓN"][0],
             "518.677.847,75")
    chequear("EFE / Distribuciones",
             efe["Distribución de resultados"][0], "(191.257.782,59)")
    chequear("EFE / 'Resultado por Tenencia' queda EN BLANCO",
             efe["Resultado por Tenencia"], ["", ""])

    # ------------------------------------------- ANEXO VI: reglas estrictas
    n_cols_vi = max(len(v) for _, _, v in D.ANEXO_VI["rows"])
    chequear("Anexo VI / 6 columnas de datos (sin comparativo 2025)", n_cols_vi, 6)

    encabezados_vi = " ".join(
        c[0] for fila in D.ANEXO_VI["head"] for c in fila)
    if "2025" in encabezados_vi:
        errores.append("[FALLA] Anexo VI / todavia aparece un encabezado 2025")
    else:
        oks.append("[OK]    Anexo VI / sin encabezado 2025")

    texto_vi = encabezados_vi + " ".join(
        c + " " + " ".join(v) for _, c, v in D.ANEXO_VI["rows"])
    texto_vi += " ".join(D.ANEXO_VI["notas_pie"])
    if "(1)" in texto_vi or "Modificado su valor original" in texto_vi:
        errores.append("[FALLA] Anexo VI / quedan marcadores o referencias (1)")
    else:
        oks.append("[OK]    Anexo VI / sin marcadores (1) ni la referencia "
                   "'Modificado su valor original...'")

    chequear("Anexo VI / total general",
             _fila(D.ANEXO_VI, "TOTALES AL 31/01/2026")[2][5], "2.979.397.317,99")
    chequear("Anexo VI / amortizaciones = depreciaciones del EFE",
             _fila(D.ANEXO_VI, "Amortizaciones (Anexo III)")[2][5], "181.282.731,64")

    # ------------------------------------------------- Anexo II: notas al pie
    pies = " ".join(D.ANEXO_II["notas_pie"])
    for marca in ("(2)", "(3)"):
        if marca in pies:
            oks.append(f"[OK]    Anexo II / nota al pie {marca} presente")
        else:
            errores.append(f"[FALLA] Anexo II / falta la nota al pie {marca}")

    return (not errores), oks + errores


if __name__ == "__main__":
    ok, detalle = verificar_puntos_de_control()
    for l in detalle:
        print(l)
    print("\nRESULTADO:", "TODOS LOS PUNTOS DE CONTROL OK" if ok else "HAY DIFERENCIAS")
    raise SystemExit(0 if ok else 1)
