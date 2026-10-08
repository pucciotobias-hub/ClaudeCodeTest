"""Diario de trades del dia: anota entradas y salidas, calcula el resultado de
cada trade y lo refleja en una planilla de Google Sheets.

El usuario dicta los trades en el chat ("compre 5 GGAL a 4510", "cerre el 2 a
4532") y la sesion de Claude corre este script. La verdad vive aca, en
diario/trades/<fecha>.json (gitignoreado: son operaciones personales); la
planilla es un espejo que se reescribe entera en cada cambio, asi nunca queda a
medias. Si no hay planilla configurada o no hay red, el trade queda anotado
igual y se avisa.

Resultado = (salida - entrada) x cantidad x multiplicador, con signo invertido si
el trade es vendido. No descuenta comisiones ni derechos de mercado.

Uso:
    python diario/diario.py abrir GGAL compra 5 4510 [--hora 11:32] [--nota "rebote en el piso"]
    python diario/diario.py cerrar 1 4532 [--cantidad 2] [--hora 12:05] [--nota ...]
    python diario/diario.py nota 1 "sali antes por el dato de empleo"
    python diario/diario.py borrar 1
    python diario/diario.py ver
    (todos aceptan --fecha AAAA-MM-DD; por defecto, hoy)

Planilla: DIARIO_SHEET_URL en el .env de la raiz, con la URL de la aplicacion
web de diario/planilla.gs (ver las instrucciones al principio de ese archivo).
"""
import argparse
import json
import os
import pathlib
import sys
import urllib.request
from datetime import date, datetime

DIR = pathlib.Path(__file__).resolve().parent
REPO = DIR.parent
TRADES = DIR / "trades"

# Unidades del subyacente por contrato en Matba Rofex. Un instrumento que no esta aca vale 1 y se avisa.
MULTIPLICADOR = {"GGAL": 100, "RFX20": 1, "DLR": 1000}
ENCABEZADO = ["N°", "Instrumento", "Posición", "Cantidad", "Hora entrada", "Precio entrada", "Hora salida",
              "Precio salida", "Diferencia", "Resultado $", "Duración (min)", "Estado", "Nota"]


def env(clave):
    if os.getenv(clave):
        return os.getenv(clave)
    archivo = REPO / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if linea.startswith(clave + "="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def cargar(fecha):
    ruta = TRADES / f"{fecha}.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"fecha": fecha, "trades": []}


def guardar(d):
    TRADES.mkdir(exist_ok=True)
    (TRADES / f"{d['fecha']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def numero(texto):
    """Acepta 4510, 4510.5, 4510,5 y 4.510,50."""
    t = str(texto).strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    return float(t)


def minutos(a, b):
    h = lambda x: int(x[:2]) * 60 + int(x[3:5])
    return h(b) - h(a)


def resultado(t):
    if t.get("salida") is None:
        return None, None
    dif = (t["salida"] - t["entrada"]) * (1 if t["lado"] == "compra" else -1)
    return dif, dif * t["cantidad"] * MULTIPLICADOR.get(t["instrumento"], 1)


def buscar(d, n):
    for t in d["trades"]:
        if t["n"] == n:
            return t
    sys.exit(f"No hay trade {n} el {d['fecha']}. Abiertos: {[t['n'] for t in d['trades'] if t.get('salida') is None]}")


def filas(d):
    salida = []
    for t in sorted(d["trades"], key=lambda x: (x["hora_entrada"], x["n"])):
        dif, res = resultado(t)
        # "comprado"/"vendido" y no "compra"/"venta": cada fila es un trade entero (entrada y salida), no una orden.
        salida.append([t["n"], t["instrumento"], "comprado" if t["lado"] == "compra" else "vendido", t["cantidad"], t["hora_entrada"], t["entrada"],
                       t.get("hora_salida") or "", t.get("salida") if t.get("salida") is not None else "",
                       "" if dif is None else round(dif, 4), "" if res is None else round(res, 2),
                       minutos(t["hora_entrada"], t["hora_salida"]) if t.get("hora_salida") else "",
                       "abierto" if t.get("salida") is None else "cerrado", t.get("nota", "")])
    return salida


MOVIMIENTOS = ["Hora", "Instrumento", "Operación", "Cantidad", "Precio", "Posición", "Resultado $", "Nota"]


def movimientos(d):
    """Lo que va a la planilla: una fila por orden ejecutada, con la posicion que queda despues.

    Los trades (entrada + salida) son la cuenta interna; el usuario piensa en ordenes ("compre 12",
    "vendi 2") y una tabla de trades donde todo dice "comprado" le parecia que nunca vendia.
    Un cierre parcial parte el trade en dos con la misma entrada: aca se vuelven a juntar.
    """
    ordenes = {}
    def sumar(t, hora, lado, precio, res, entra):
        clave = (hora, t["instrumento"], lado, precio, entra)
        o = ordenes.setdefault(clave, {"cant": 0, "res": None, "notas": [], "n": t["n"]})
        o["cant"] += t["cantidad"]
        o["n"] = min(o["n"], t["n"])
        if res is not None:
            o["res"] = (o["res"] or 0) + res
        if t.get("nota") and t["nota"] not in o["notas"]:
            o["notas"].append(t["nota"])
    for t in d["trades"]:
        sumar(t, t["hora_entrada"], t["lado"], t["entrada"], None, True)
        if t.get("salida") is not None:
            sumar(t, t["hora_salida"], "venta" if t["lado"] == "compra" else "compra", t["salida"], resultado(t)[1], False)
    salida, posicion = [], {}
    # Misma hora: primero las entradas, despues las salidas, y entre iguales por numero de trade.
    for (hora, inst, lado, precio, entra), o in sorted(ordenes.items(), key=lambda x: (x[0][0], not x[0][4], x[1]["n"])):
        firmada = o["cant"] if lado == "compra" else -o["cant"]
        posicion[inst] = posicion.get(inst, 0) + firmada
        salida.append([hora, inst, lado, firmada, precio, posicion[inst],
                       "" if o["res"] is None else round(o["res"], 2), " · ".join(o["notas"])])
    return salida


def resumen(d):
    res = [resultado(t)[1] for t in d["trades"] if t.get("salida") is not None]
    gan, per = [r for r in res if r > 0], [r for r in res if r < 0]
    # El acierto va como texto ("7 de 8 (88%)"): con "88%" a secas la planilla lo tomaba como porcentaje y
    # le pegaba ese formato a las celdas vecinas del resumen (8 trades cerrados se veian "800%").
    plata = lambda x: "$ " + f"{x:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return [
        ["Resultado del día $", round(sum(res), 2)],
        ["Trades cerrados", len(res)],
        ["Ganadores", len(gan)],
        ["Perdedores", len(per)],
        ["Acierto", f"{len(gan)} de {len(res)} ({len(gan) / len(res):.0%})" if res else "—"],
        ["Ganancia promedio", plata(sum(gan) / len(gan)) if gan else "—"],
        ["Pérdida promedio", plata(sum(per) / len(per)) if per else "—"],
        ["Mejor trade", plata(max(res)) if res else "—"],
        ["Peor trade", plata(min(res)) if res else "—"],
        ["Abiertos", sum(1 for t in d["trades"] if t.get("salida") is None)],
    ]


def sincronizar(d):
    url = env("DIARIO_SHEET_URL")
    if not url:
        return "planilla: sin configurar (falta DIARIO_SHEET_URL en .env); quedó anotado solo acá"
    cuerpo = json.dumps({"fecha": d["fecha"], "encabezado": MOVIMIENTOS, "filas": movimientos(d), "resumen": resumen(d)}).encode("utf-8")
    try:
        pedido = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(pedido, timeout=40) as r:   # Apps Script contesta con una redireccion; urllib la sigue
            texto = r.read().decode("utf-8")
        r = json.loads(texto)
        return f"planilla: actualizada ({r.get('url', 'ok')})" if r.get("ok") else f"planilla: rechazó el envío ({r.get('error')})"
    except Exception as e:
        return f"planilla: NO se pudo actualizar ({type(e).__name__}: {str(e)[:120]}); quedó anotado acá, se reintenta con el próximo cambio"


def mostrar(d):
    print(f"Diario {d['fecha']}")
    for f in filas(d):
        n, inst, lado, cant, he, pe, hs, ps, dif, res, dur, estado, nota = f
        cola = f"-> {hs} a {ps}  dif {dif:+g}  resultado $ {res:+,.2f}  ({dur} min)" if estado == "cerrado" else "ABIERTO"
        print(f"  #{n} {he} {lado} {cant} {inst} a {pe}  {cola}" + (f"  | {nota}" if nota else ""))
    for rot, val in resumen(d):
        print(f"  {rot}: {val}")


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--fecha", default=date.today().isoformat())
    sub = a.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("abrir")
    p.add_argument("instrumento"); p.add_argument("lado", choices=["compra", "venta"])
    p.add_argument("cantidad", type=int); p.add_argument("precio"); p.add_argument("--hora"); p.add_argument("--nota", default="")
    p = sub.add_parser("cerrar")
    p.add_argument("n", type=int); p.add_argument("precio"); p.add_argument("--cantidad", type=int)
    p.add_argument("--hora"); p.add_argument("--nota")
    p = sub.add_parser("nota"); p.add_argument("n", type=int); p.add_argument("texto")
    p = sub.add_parser("borrar"); p.add_argument("n", type=int)
    sub.add_parser("ver")
    arg = a.parse_args()

    d = cargar(arg.fecha)
    ahora = datetime.now().strftime("%H:%M")
    if arg.orden == "abrir":
        inst = arg.instrumento.upper()
        if inst not in MULTIPLICADOR:
            print(f"AVISO: no conozco el multiplicador de {inst}; uso 1. Agregalo en MULTIPLICADOR.")
        n = max([t["n"] for t in d["trades"]], default=0) + 1
        d["trades"].append({"n": n, "instrumento": inst, "lado": arg.lado, "cantidad": arg.cantidad,
                            "hora_entrada": arg.hora or ahora, "entrada": numero(arg.precio), "nota": arg.nota})
    elif arg.orden == "cerrar":
        t = buscar(d, arg.n)
        if t.get("salida") is not None:
            sys.exit(f"El trade {arg.n} ya está cerrado.")
        cant = arg.cantidad or t["cantidad"]
        if cant > t["cantidad"]:
            sys.exit(f"El trade {arg.n} tiene {t['cantidad']} contratos, no {cant}.")
        if cant < t["cantidad"]:   # cierre parcial: lo que sigue abierto pasa a un trade nuevo con la misma entrada
            resto = dict(t, n=max(x["n"] for x in d["trades"]) + 1, cantidad=t["cantidad"] - cant)
            d["trades"].append(resto)
            t["cantidad"] = cant
            print(f"Cierre parcial: quedan {resto['cantidad']} contratos abiertos como trade #{resto['n']}.")
        t.update(salida=numero(arg.precio), hora_salida=arg.hora or ahora)
        if arg.nota:
            t["nota"] = (t.get("nota", "") + " · " + arg.nota).strip(" ·")
    elif arg.orden == "nota":
        t = buscar(d, arg.n)
        t["nota"] = (t.get("nota", "") + " · " + arg.texto).strip(" ·")
    elif arg.orden == "borrar":
        d["trades"].remove(buscar(d, arg.n))

    if arg.orden != "ver":
        guardar(d)
    mostrar(d)
    if arg.orden != "ver" or env("DIARIO_SHEET_URL"):
        print(sincronizar(d))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
