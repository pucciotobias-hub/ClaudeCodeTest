"""Tablero de tasas de los futuros de A3 (ex Matba Rofex), en vivo.

Lee la pagina publica "A3 - Realtime" (mtr.primary.ventures), que entrega sin
login las puntas, el ultimo, el volumen y el interes abierto de los futuros
financieros: la lista de contratos sale de /api/v2/ref-data y los precios llegan
por websocket. No tiene API documentada: si cambian el formato, esto se rompe y
el tablero lo dice (campo "error" / "edadSeg" de /datos) en vez de mostrar
numeros viejos como si fueran de ahora.

Con eso arma tres cosas (ver calcular()):
  1. Curva de tasas implicitas del dolar futuro contra el dolar spot, comparada
     con la caucion a 1 dia.
  2. Pases entre vencimientos consecutivos (DLR, GGAL, RFX20).
  3. Interes abierto y volumen por contrato. El feed solo trae el dato de hoy,
     asi que la historia se arma aca: una foto por dia en tasas/historia/.

Uso:  pythonw tasas/servidor.py      (lo levanta solo abrir_tasas.ps1)
"""
import asyncio
import json
import re
import threading
import time
import urllib.request
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import websockets

PUERTO = 8766
DIR = Path(__file__).resolve().parent
HISTORIA = DIR / "historia"
ORIGEN = "https://mtr.primary.ventures"
URL_REF = ORIGEN + "/api/v2/ref-data"
URL_WS = "wss://mtr.primary.ventures/ws?session_id=&conn_id="
PING_SEG = 40  # el mismo intervalo que usa la pagina

# Orden de los campos de un tick "M:" (sale de applyData en el main.js de la pagina).
CAMPOS = "id seq bsz bid ask asz lst lstd von vol voe low hgh opn oin refp refd cls clsd stl stld".split()
NUMERICOS = {"bsz", "bid", "ask", "asz", "lst", "von", "low", "hgh", "opn", "oin", "refp", "cls", "stl"}

FUTURO = re.compile(r"^rx_(?:DDF_DLR|DUAL_GGAL|DUAL_RFX20)_([A-Z]{3}\d{2})(M)?$")
PASE = re.compile(r"^rx_DDF_DLR_([A-Z]{3}\d{2})_([A-Z]{3}\d{2})(_M)?$")
TASA_PESOS = re.compile(r"^rx_DUAL_(CAUC|TMR)_([A-Z]{3}\d{2})$")
CAUCION = re.compile(r"^rx_MAE_CAARS_(\d+)D$")
SPOT = "rx_DDF_DLR_SPOT"
MESES = "ENE FEB MAR ABR MAY JUN JUL AGO SEP OCT NOV DIC".split()
# Puntas mas abiertas que esto (en % del precio) no dicen nada sobre la tasa: el
# medio de 1921 / 1999 no es un precio. Se muestran, pero marcadas.
ANCHO_PCT = 0.5

candado = threading.Lock()
ticks = {}        # id -> dict con los campos del ultimo tick
contratos = {}    # id -> {"activo", "mes", "vto", "m"} para los futuros
ids = []          # todo lo que se suscribe
estado = {"conectado": False, "ultimoTick": 0.0, "error": None, "fechaRef": None}


def cargar_referencia():
    """Baja la lista de contratos y arma que suscribir. El vencimiento sale de
    daysToExpiration, que es relativo al dia en que se pide."""
    pedido = urllib.request.Request(URL_REF, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(pedido, timeout=60) as r:
        ref = json.load(r)
    hoy = date.today()
    nuevos, lista = {}, []
    for s in ref["securities"]:
        i = s["id"]
        m = FUTURO.match(i)
        if m and (s.get("cfiCode") or "").startswith("F") and s.get("daysToExpiration") is not None:
            activo = "DLR" if "_DLR_" in i else "GGAL" if "_GGAL_" in i else "RFX20"
            nuevos[i] = {"activo": activo, "mes": m.group(1), "m": bool(m.group(2)),
                         "vto": hoy + timedelta(days=int(s["daysToExpiration"]))}
            lista.append(i)
        elif PASE.match(i) or TASA_PESOS.match(i) or CAUCION.match(i) or i == SPOT:
            lista.append(i)
    if not nuevos:
        raise RuntimeError("ref-data no trajo futuros: cambio el formato")
    with candado:
        contratos.clear()
        contratos.update(nuevos)
        ids[:] = lista
        estado["fechaRef"] = hoy


def aplicar(mensaje):
    """Un mensaje es un tick suelto o un array JSON de ticks. Solo interesan los M:."""
    if mensaje == "pong" or not mensaje:
        return
    crudos = json.loads(mensaje) if mensaje[0] == "[" else [mensaje]
    with candado:
        for c in crudos:
            if not c.startswith("M:"):
                continue
            partes = c[2:].split("|")
            t = {}
            for k, v in zip(CAMPOS, partes):
                if k in NUMERICOS:
                    try:
                        t[k] = float(v) if v != "" else None
                    except ValueError:
                        t[k] = None
                else:
                    t[k] = v
            ticks[t["id"]] = t
            estado["ultimoTick"] = time.time()


async def escuchar():
    espera = 2
    while True:
        try:
            if estado["fechaRef"] != date.today():
                await asyncio.to_thread(cargar_referencia)
            async with websockets.connect(URL_WS, origin=ORIGEN, user_agent_header="Mozilla/5.0",
                                          ping_interval=None, max_size=None) as ws:
                await ws.send(json.dumps({"_req": "S", "topicType": "md",
                                          "topics": ["md." + i for i in ids], "replace": False}))
                estado.update(conectado=True, error=None)
                espera = 2
                ultimo_ping = time.time()
                while estado["fechaRef"] == date.today():
                    try:
                        aplicar(await asyncio.wait_for(ws.recv(), 5))
                    except asyncio.TimeoutError:
                        pass
                    if time.time() - ultimo_ping > PING_SEG:
                        await ws.send("ping")
                        ultimo_ping = time.time()
        except Exception as e:  # red caida, formato cambiado, lo que sea: se reintenta
            estado.update(conectado=False, error=f"{type(e).__name__}: {e}"[:200])
        estado["conectado"] = False
        await asyncio.sleep(espera)
        espera = min(espera * 2, 60)


# --- Cuentas -----------------------------------------------------------------

def tasas(futuro, base, dias):
    """Tasa implicita de pasar de `base` a `futuro` en `dias`: TNA simple, TEA y
    efectiva mensual, en %."""
    if not futuro or not base or dias <= 0:
        return None
    directa = futuro / base - 1
    return {"tna": directa * 365 / dias * 100,
            "tea": ((1 + directa) ** (365 / dias) - 1) * 100,
            "tem": ((1 + directa) ** (30 / dias) - 1) * 100}


def referencia(t):
    """Precio con el que se hacen las cuentas de un contrato: el medio de las
    puntas si estan las dos, si no el ultimo, si no el ajuste previo."""
    if not t:
        return None, None
    if t.get("bid") and t.get("ask"):
        return (t["bid"] + t["ask"]) / 2, "puntas"
    if t.get("lst"):
        return t["lst"], "ultimo"
    if t.get("stl"):
        return t["stl"], "ajuste"
    return None, None


def foto_previa(hoy):
    """La foto de interes abierto del ultimo dia anterior a hoy que haya quedado guardada."""
    try:
        previas = sorted(f for f in HISTORIA.glob("*.json") if f.stem < hoy.isoformat())
    except OSError:
        return None, {}
    if not previas:
        return None, {}
    try:
        return previas[-1].stem, json.loads(previas[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, {}


def calcular():
    with candado:
        tk = {k: dict(v) for k, v in ticks.items()}
        ct = dict(contratos)
    hoy = date.today()

    spot_t = tk.get(SPOT, {})
    spot = spot_t.get("lst") or spot_t.get("refp")
    spot_prev = spot_t.get("stl")

    # Caucion en pesos por plazo. Viene como TNA.
    cauciones = []
    for i, t in tk.items():
        m = CAUCION.match(i)
        if m and (t.get("bid") or t.get("ask") or t.get("lst")):
            cauciones.append({"plazo": int(m.group(1)), "bid": t.get("bid"), "ask": t.get("ask"),
                              "ultimo": t.get("lst"), "ajuste": t.get("stl"), "monto": t.get("von")})
    cauciones.sort(key=lambda c: c["plazo"])
    c1 = next((c for c in cauciones if c["plazo"] == 1), None)
    cau_tna = None
    if c1:
        cau_tna = (c1["bid"] + c1["ask"]) / 2 if c1["bid"] and c1["ask"] else c1["ultimo"]
    cau_tea = ((1 + cau_tna / 100 / 365) ** 365 - 1) * 100 if cau_tna else None

    tasas_pesos = []
    for i, t in tk.items():
        m = TASA_PESOS.match(i)
        if m:
            tasas_pesos.append({"contrato": ("Caución" if m.group(1) == "CAUC" else "TAMAR") + " " + m.group(2),
                                "orden": (m.group(1), m.group(2)[3:], MESES.index(m.group(2)[:3])), "bid": t.get("bid"),
                                "ask": t.get("ask"), "ultimo": t.get("lst"), "ajuste": t.get("stl")})

    # Un contrato = el libro comun + el libro M (mismo vencimiento, mismo interes abierto).
    grupos = {}
    for i, c in ct.items():
        g = grupos.setdefault((c["activo"], c["mes"]), {"activo": c["activo"], "mes": c["mes"], "vto": c["vto"]})
        g["m" if c["m"] else "comun"] = tk.get(i)
    orden = sorted(grupos.values(), key=lambda g: (g["activo"], g["vto"]))

    fecha_prev, prev = foto_previa(hoy)
    curva, interes, foto = [], [], {}
    for g in orden:
        comun, libro_m = g.get("comun") or {}, g.get("m") or {}
        t = comun if (comun.get("bid") or comun.get("ask") or comun.get("lst")) else (libro_m or comun)
        dias = (g["vto"] - hoy).days
        nombre = f"{g['activo']}/{g['mes']}"
        ref, base = referencia(t)
        vol = (comun.get("von") or 0) + (libro_m.get("von") or 0)
        oi = max(comun.get("oin") or 0, libro_m.get("oin") or 0) or None
        ajuste = t.get("stl")
        fila = {"contrato": nombre, "vto": g["vto"].isoformat(), "dias": dias, "bid": t.get("bid"),
                "ask": t.get("ask"), "ultimo": t.get("lst"), "ajuste": ajuste, "ref": ref, "base": base,
                "var": (ref / ajuste - 1) * 100 if ref and ajuste else None,
                "ancho": bool(t.get("bid") and t.get("ask") and (t["ask"] - t["bid"]) / ref * 100 > ANCHO_PCT)}
        if g["activo"] == "DLR" and ref:
            fila["tasa"] = tasas(ref, spot, dias)
            fila["tasaBid"] = tasas(t.get("bid"), spot, dias)
            fila["tasaAsk"] = tasas(t.get("ask"), spot, dias)
            if fila["tasa"] and cau_tea is not None:
                fila["vsCaucion"] = fila["tasa"]["tea"] - cau_tea
            curva.append(fila)
        if oi or vol:
            p = prev.get(nombre, {})
            interes.append({"activo": g["activo"], "contrato": nombre, "dias": dias, "oi": oi,
                            "oiPrev": p.get("oi"), "dOi": oi - p["oi"] if oi and p.get("oi") else None,
                            "vol": vol, "volM": libro_m.get("von") or 0, "volPrev": p.get("vol"),
                            "ultimo": t.get("lst") or ajuste})
            foto[nombre] = {"oi": oi, "vol": vol, "ultimo": t.get("lst"), "ajuste": ajuste}
        g["fila"] = fila
        g["t"] = t

    # Pases: tramo entre vencimientos consecutivos de cada activo.
    pases = []
    for activo in ("DLR", "GGAL", "RFX20"):
        serie = [g for g in orden if g["activo"] == activo]
        for cerca, lejos in zip(serie, serie[1:]):
            dias = (lejos["vto"] - cerca["vto"]).days
            f1 = cerca["fila"]["ref"]
            if not f1 or dias <= 0:
                continue
            bid = ask = None
            fuente = None
            if activo == "DLR":  # el pase cotiza como contrato propio
                for sufijo in ("", "_M"):
                    p = tk.get(f"rx_DDF_DLR_{cerca['mes']}_{lejos['mes']}{sufijo}")
                    if p and p.get("bid") and p.get("ask"):
                        bid, ask, fuente = p["bid"], p["ask"], "contrato" if not sufijo else "contrato M"
                        break
            if fuente is None:
                a, b = cerca["t"], lejos["t"]
                if a.get("bid") and a.get("ask") and b.get("bid") and b.get("ask"):
                    bid, ask, fuente = b["bid"] - a["ask"], b["ask"] - a["bid"], "puntas"
                elif lejos["fila"]["ref"]:
                    bid = ask = lejos["fila"]["ref"] - f1
                    fuente = "referencia"
                else:
                    continue
            medio = (bid + ask) / 2
            pases.append({"activo": activo, "tramo": f"{cerca['mes']} → {lejos['mes']}", "dias": dias,
                          "bid": bid, "ask": ask, "fuente": fuente, "tasa": tasas(f1 + medio, f1, dias),
                          "tnaBid": bid / f1 * 365 / dias * 100, "tnaAsk": ask / f1 * 365 / dias * 100,
                          "pct": medio / f1 * 100, "ancho": (ask - bid) / f1 * 100 > ANCHO_PCT})

    guardar_foto(hoy, foto)
    edad = time.time() - estado["ultimoTick"] if estado["ultimoTick"] else None
    return {
        "ahora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "conectado": estado["conectado"], "edadSeg": edad, "error": estado["error"],
        "spot": {"ultimo": spot, "ajuste": spot_prev, "hora": spot_t.get("lstd"),
                 "var": (spot / spot_prev - 1) * 100 if spot and spot_prev else None},
        "caucion": {"tna": cau_tna, "tea": cau_tea, "plazos": cauciones},
        "tasasPesos": [{k: v for k, v in x.items() if k != "orden"}
                       for x in sorted(tasas_pesos, key=lambda x: x["orden"])],
        "curva": curva, "pases": pases, "interes": interes, "fechaPrev": fecha_prev,
    }


ultima_foto = 0.0


def guardar_foto(hoy, foto):
    """Una foto por dia, pisada cada minuto mientras haya datos: el ultimo valor
    visto del dia es el que queda. Sin datos no se escribe nada."""
    global ultima_foto
    if not foto or not estado["conectado"] or time.time() - ultima_foto < 60:
        return
    try:
        HISTORIA.mkdir(exist_ok=True)
        (HISTORIA / f"{hoy.isoformat()}.json").write_text(
            json.dumps(foto, ensure_ascii=False, indent=1), encoding="utf-8")
        ultima_foto = time.time()
    except OSError:
        pass


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def responder(self, cuerpo, tipo):
        datos = cuerpo.encode("utf-8") if isinstance(cuerpo, str) else cuerpo
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta == "/datos":
            self.responder(json.dumps(calcular(), ensure_ascii=False), "application/json; charset=utf-8")
        elif ruta in ("/", "/index.html"):
            self.responder((DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_error(404)


if __name__ == "__main__":
    threading.Thread(target=lambda: asyncio.run(escuchar()), daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()
