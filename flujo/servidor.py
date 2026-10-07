"""Tablero de flujo del ADR de GGAL (NASDAQ): como viene la compra y la venta
hoy, en la semana y en las ultimas semanas.

No hay datos tick a tick (son pagos), asi que el flujo se aproxima con velas de
5 minutos de yfinance, que entrega unas 60 ruedas hacia atras:

  - Delta de una vela = volumen x (2*cierre - maximo - minimo) / (maximo - minimo).
    Una vela que cierra en su maximo cuenta todo su volumen como compra, una que
    cierra en el minimo como venta, y una que cierra en el medio da cero. Es una
    estimacion: no dice quien agredio, dice hacia donde resolvio cada 5 minutos.
  - VWAP anclado: precio promedio ponderado por volumen desde el inicio del dia,
    de la semana o del mes.
  - Volumen relativo: el volumen acumulado hasta esta hora contra el promedio de
    las 20 ruedas anteriores a la misma hora.
  - Perfil de volumen: a que precios se opero mas en la semana.

El volumen de las velas de 5 minutos no incluye las subastas de apertura y
cierre, por eso suma algo menos que el volumen diario oficial. Las variaciones
de precio si salen de los cierres diarios oficiales.

La pagina trae ademas un chat para preguntar lo que no se entiende (ver chat()):
cada pregunta se le pasa a `claude -p` junto con los numeros que el tablero esta
mostrando en ese momento. Usa la cuenta de Claude Code de esta maquina, sin
herramientas: solo lee lo que se le manda y contesta.

Uso:  pythonw flujo/servidor.py      (lo levanta solo abrir_flujo.ps1)
"""
import json
import re
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import yfinance as yf

PUERTO = 8767
DIR = Path(__file__).resolve().parent
SIMBOLO = "GGAL"
HUSO = "America/Argentina/Buenos_Aires"
VIGENCIA_SEG = 60       # no pedirle a yfinance mas de una vez por minuto
RUEDAS_PROMEDIO = 20    # base del volumen relativo
ESCALON = 0.10          # alto de cada escalon del perfil de volumen, en USD
CLAUDE = Path.home() / ".local" / "bin" / "claude.exe"
MODELO_CHAT = "sonnet"
# Carpeta neutra para correr claude: desde el repo cargaria CLAUDE.md y la memoria del proyecto.
DIR_CHAT = Path(tempfile.gettempdir()) / "flujo-chat"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SISTEMA = """Sos el ayudante del tablero de flujo del ADR de GGAL (Grupo Financiero Galicia, NASDAQ) de Tobías, operador de futuros en Matba Rofex. Él te pregunta lo que no entiende del tablero; en cada mensaje recibís los números que el tablero muestra en ese momento y después su pregunta.

Cómo se calcula cada cosa (velas de 5 minutos de yfinance, últimas 60 ruedas):
- Delta de una vela = volumen × (2×cierre − máximo − mínimo) / (máximo − mínimo). Cierra en el máximo: todo compra; en el mínimo: todo venta; en el medio: cero. Es una estimación, no el flujo real de órdenes. "deltaPct" es el delta neto como porcentaje del volumen.
- VWAP anclado: precio promedio ponderado por volumen desde el inicio del día, de la semana o del mes. "vsVwap" es la distancia del precio a ese VWAP, en porcentaje.
- Volumen relativo ("rvol"): volumen acumulado hasta esta hora contra el promedio de las 20 ruedas anteriores a la misma hora; 1,0 es normal.
- "gap" es el salto entre el cierre anterior y la apertura; "intra" es lo que se movió con el mercado abierto. El delta solo ve lo intradía: no ve gaps ni subastas.
- Perfil de volumen: volumen por escalón de 0,10 USD en la semana. POC = precio más operado; área de valor (val a vah) = franja que concentra el 70% del volumen.

Cómo contestar:
- En español rioplatense, claro y corto: lo justo para que se entienda, sin relleno. Texto plano, sin títulos ni tablas; como mucho alguna palabra en **negrita**.
- Explicá con los números del tablero de ahora, no en abstracto.
- No inventes datos que no estén en lo que recibiste. Si pregunta por algo que el tablero no tiene (noticias, niveles del gráfico, opciones, la plaza local), decilo.
- Podés decir qué sugiere la lectura del flujo y qué la confirmaría o la desmentiría, pero no des órdenes de compra o venta."""

DIAS = "Lun Mar Mié Jue Vie Sáb Dom".split()
MESES = "ene feb mar abr may jun jul ago sep oct nov dic".split()

_cache = {"cuando": 0.0, "datos": None}
_candado = threading.Lock()


def r(x, n=2):
    """Redondea para el JSON; NaN e infinito salen como null."""
    x = float(x)
    return round(x, n) if np.isfinite(x) else None


def pct(a, b):
    return r((a / b - 1) * 100) if b else None


def coma(x, formato):
    return format(x, formato).replace(".", ",")


def dia_corto(f):
    return f"{DIAS[f.weekday()]} {f.day:02d}"


def fecha_corta(f):
    return f"{f.day:02d}-{MESES[f.month - 1]}"


def perfil(v):
    """Volumen por escalon de precio: el de cada vela se reparte parejo entre su minimo y su maximo."""
    if v.empty:
        return None
    piso = np.floor(v.Low.min() / ESCALON) * ESCALON
    n = int(np.floor((v.High.max() - piso) / ESCALON)) + 1
    vol, delta = np.zeros(n), np.zeros(n)
    for lo, hi, vo, de in zip(v.Low, v.High, v.Volume, v.delta):
        a = int((lo - piso) / ESCALON)
        b = min(int((hi - piso) / ESCALON), n - 1)
        vol[a:b + 1] += vo / (b - a + 1)
        delta[a:b + 1] += de / (b - a + 1)
    poc = int(vol.argmax())
    # Area de valor: el 70% del volumen, creciendo desde el escalon mas operado.
    a = b = poc
    dentro = vol[poc]
    while dentro < 0.7 * vol.sum() and (a > 0 or b < n - 1):
        abajo = vol[a - 1] if a > 0 else -1
        arriba = vol[b + 1] if b < n - 1 else -1
        if arriba >= abajo:
            b += 1
            dentro += arriba
        else:
            a -= 1
            dentro += abajo
    return {
        "escalones": [{"p": r(piso + i * ESCALON), "v": int(vol[i]), "d": int(delta[i])} for i in range(n)],
        "poc": r(piso + poc * ESCALON), "val": r(piso + a * ESCALON), "vah": r(piso + (b + 1) * ESCALON),
    }


def lectura(intra, gaps, delta_pct, vs_vwap, que):
    """Una frase que cruza precio, delta y VWAP. Reglas simples, a proposito.

    El delta solo ve lo que pasa con el mercado abierto, asi que se compara con el
    movimiento intradia y no con la variacion total: un gap no tiene volumen.
    """
    if intra is None or delta_pct is None:
        return ""
    sube = intra > 0
    if abs(delta_pct) < 3:
        flujo = "sin flujo neto claro, compra y venta parejas"
    elif (delta_pct > 0) == sube:
        flujo = ("la suba intradía vino con compra neta" if sube else "la baja intradía vino con venta neta") + ", el flujo acompaña al precio"
    else:
        flujo = ("el precio sube con el mercado abierto pero el flujo neto es vendedor" if sube else "el precio baja con el mercado abierto pero el flujo neto es comprador") + " (divergencia)"
    if gaps is not None and abs(gaps) >= 1 and abs(gaps) > abs(intra):
        flujo += f". Ojo: la mayor parte del movimiento fue por gaps de apertura ({coma(gaps, '+.1f')}%), que el delta no ve"
    lado = "arriba" if vs_vwap >= 0 else "abajo"
    quien = "el comprador promedio va ganando" if vs_vwap >= 0 else "el comprador promedio está en pérdida"
    return f"{que}: {flujo}. Precio {coma(abs(vs_vwap), '.2f')}% {lado} del VWAP: {quien}."


def calcular():
    t = yf.Ticker(SIMBOLO)
    v = t.history(period="60d", interval="5m", prepost=False, auto_adjust=False)
    d = t.history(period="6mo", interval="1d", auto_adjust=False)
    if v.empty or d.empty:
        raise RuntimeError("yfinance no devolvió velas")
    v = v[v.Volume > 0].copy()
    rango = (v.High - v.Low).replace(0, np.nan)
    v["delta"] = (v.Volume * (2 * v.Close - v.High - v.Low) / rango).fillna(0.0)
    v["pv"] = (v.High + v.Low + v.Close) / 3 * v.Volume
    v["fecha"] = v.index.date
    v["hora"] = v.index.strftime("%H:%M")                       # hora de Nueva York: define la franja
    v["hora_ar"] = v.index.tz_convert(HUSO).strftime("%H:%M")   # la que se muestra
    iso = v.index.isocalendar()
    v["semana"] = (iso.year.astype(int) * 100 + iso.week.astype(int)).values
    v["mes"] = v.index.year * 100 + v.index.month

    def vwap(clave):
        g = v.groupby(clave)
        return g.pv.cumsum() / g.Volume.cumsum()

    v["vwap_dia"], v["vwap_sem"], v["vwap_mes"] = vwap("fecha"), vwap("semana"), vwap("mes")
    v["vol_acum"] = v.groupby("fecha").Volume.cumsum()
    v["delta_dia"] = v.groupby("fecha").delta.cumsum()

    cierres = {i.date(): c for i, c in d.Close.items()}
    fechas = sorted(v.fecha.unique())
    hoy = fechas[-1]

    # ---- una fila por rueda
    dias = []
    for f in fechas:
        x = v[v.fecha == f]
        ant = [c for g, c in cierres.items() if g < f]
        cierre = cierres.get(f, x.Close.iloc[-1]) if f != hoy else x.Close.iloc[-1]
        dias.append({
            "fecha": f.isoformat(), "dia": dia_corto(f), "semana": int(x.semana.iloc[0]),
            "c": r(cierre), "var": pct(cierre, ant[-1]) if ant else None,
            "gap": pct(x.Open.iloc[0], ant[-1]) if ant else None, "intra": pct(x.Close.iloc[-1], x.Open.iloc[0]),
            "vol": int(x.Volume.sum()), "delta": int(x.delta.sum()),
            "deltaPct": r(x.delta.sum() / x.Volume.sum() * 100, 1),
            "vwap": r(x.vwap_dia.iloc[-1]), "vsVwap": pct(x.Close.iloc[-1], x.vwap_dia.iloc[-1]),
            "velas": len(x),
        })
    for i, f in enumerate(dias):
        base = [g["vol"] for g in dias[max(0, i - RUEDAS_PROMEDIO):i] if g["velas"] >= 60]
        f["rvol"] = r(f["vol"] / np.mean(base)) if len(base) >= 5 and (f["velas"] >= 60 or i == len(dias) - 1) else None

    # ---- hoy, vela por vela, contra el promedio de las ruedas anteriores a la misma hora
    x = v[v.fecha == hoy]
    previas = v[v.fecha.isin(fechas[-1 - RUEDAS_PROMEDIO:-1])]
    prom_acum = previas.groupby("hora").vol_acum.mean()
    prom_vela = previas.groupby("hora").Volume.mean()
    barras = [{
        "t": b.hora_ar, "c": r(b.Close), "vwap": r(b.vwap_dia), "v": int(b.Volume), "d": int(b.delta),
        "dAcum": int(b.delta_dia), "vProm": int(prom_vela.get(b.hora, 0)),
    } for b in x.itertuples()]
    base_hora = prom_acum.get(x.hora.iloc[-1])
    rvol_hoy = r(x.Volume.sum() / base_hora) if base_hora else None
    dias[-1]["rvol"] = rvol_hoy   # la rueda en curso se compara a la misma hora, no contra el dia entero
    h = dias[-1]
    bloque_hoy = {
        "fecha": hoy.isoformat(), "dia": dia_corto(hoy), "precio": h["c"], "var": h["var"],
        "vwap": h["vwap"], "vsVwap": h["vsVwap"], "delta": h["delta"], "deltaPct": h["deltaPct"],
        "vol": h["vol"], "rvol": rvol_hoy, "barras": barras, "completa": len(x) >= 78,
        "gap": h["gap"], "intra": h["intra"],
        "lectura": lectura(h["intra"], h["gap"], h["deltaPct"], h["vsVwap"], "Hoy"),
    }

    # ---- una fila por semana
    semanas = []
    for s, x in v.groupby("semana"):
        fs = sorted(x.fecha.unique())
        ant = [c for g, c in cierres.items() if g < fs[0]]
        cierre = x.Close.iloc[-1] if fs[-1] == hoy else cierres.get(fs[-1], x.Close.iloc[-1])
        fin = x.groupby("fecha").last()   # ruedas que cerraron arriba del VWAP semanal de ese momento
        arriba = int((fin.Close >= fin.vwap_sem).sum())
        de_la_semana = [g for g in dias if g["semana"] == s]
        compone = lambda k: r((np.prod([1 + (g[k] or 0) / 100 for g in de_la_semana]) - 1) * 100)
        fila = {
            "gap": compone("gap"), "intra": compone("intra"),
            "semana": int(s), "desde": fecha_corta(fs[0]), "hasta": fecha_corta(fs[-1]), "ruedas": len(fs),
            "c": r(cierre), "var": pct(cierre, ant[-1]) if ant else None,
            "vol": int(x.Volume.sum()), "delta": int(x.delta.sum()),
            "deltaPct": r(x.delta.sum() / x.Volume.sum() * 100, 1),
            "vwap": r(x.vwap_sem.iloc[-1]), "vsVwap": pct(x.Close.iloc[-1], x.vwap_sem.iloc[-1]),
            "diasArriba": arriba, "enCurso": bool(s == v.semana.iloc[-1]),
        }
        semanas.append(fila)
    sem = semanas[-1]
    sem["lectura"] = lectura(sem["intra"], sem["gap"], sem["deltaPct"], sem["vsVwap"], "Semana")

    # ---- serie de 30 minutos de las ultimas 20 ruedas: precio, VWAP semanal y mensual, delta acumulado
    z = v[v.fecha.isin(fechas[-RUEDAS_PROMEDIO:])].copy()
    z["dAcum"] = z.delta.cumsum()
    z = z[(z.index.minute % 30 == 25) | (z.index == z.index[-1])]
    serie = [{
        "f": b.fecha.isoformat(), "t": f"{dia_corto(b.fecha)} {b.hora_ar}", "c": r(b.Close),
        "vwapSem": r(b.vwap_sem), "vwapMes": r(b.vwap_mes), "dAcum": int(b.dAcum),
    } for b in z.itertuples()]

    ultima = v.index[-1].tz_convert(HUSO)
    edad = (datetime.now(ultima.tzinfo) - ultima).total_seconds()
    return {
        "simbolo": SIMBOLO, "actualizado": datetime.now().isoformat(timespec="seconds"),
        "ultimaVela": f"{dia_corto(ultima.date())} {ultima:%H:%M}", "enRueda": bool(edad < 15 * 60),
        "hoy": bloque_hoy, "semana": sem,
        "mes": {"vwap": r(v.vwap_mes.iloc[-1]), "vsVwap": pct(v.Close.iloc[-1], v.vwap_mes.iloc[-1])},
        "dias": dias, "semanas": semanas, "serie": serie,
        "perfil": {
            "actual": perfil(v[v.semana == semanas[-1]["semana"]]),
            "previa": perfil(v[v.semana == semanas[-2]["semana"]]) if len(semanas) > 1 else None,
        },
    }


def datos():
    with _candado:
        if _cache["datos"] is None or time.time() - _cache["cuando"] > VIGENCIA_SEG:
            try:
                _cache["datos"] = calcular()
            except Exception as e:  # sin red o yfinance caido: devolver lo ultimo que hubo, avisando
                viejo = dict(_cache["datos"] or {})
                viejo["error"] = f"{type(e).__name__}: {e}"
                return viejo
            _cache["cuando"] = time.time()
        return _cache["datos"]


def foto_para_chat():
    """Lo que el tablero muestra ahora, resumido para mandarselo a Claude con cada pregunta."""
    d = datos()
    if not d.get("hoy"):
        return {"error": d.get("error", "sin datos")}
    hoy = {k: v for k, v in d["hoy"].items() if k != "barras"}
    hoy["velas"] = [{k: b[k] for k in ("t", "c", "vwap", "v", "vProm", "dAcum")} for b in d["hoy"]["barras"][-24:]]
    area = lambda p: p and {"poc": p["poc"], "val": p["val"], "vah": p["vah"]}
    return {
        "ultimaVela": d["ultimaVela"], "mercadoAbierto": d["enRueda"], "hoy": hoy, "mes": d["mes"],
        "ruedas": [{k: g[k] for k in ("dia", "fecha", "c", "var", "gap", "intra", "deltaPct", "vol", "rvol", "vsVwap")}
                   for g in d["dias"][-15:]],
        "semanas": d["semanas"][-8:],
        "perfilSemanaEnCurso": area(d["perfil"]["actual"]), "perfilSemanaAnterior": area(d["perfil"]["previa"]),
    }


def chat(pregunta, sesion, primera):
    """Genera la respuesta de Claude de a pedazos, a medida que la escribe."""
    DIR_CHAT.mkdir(exist_ok=True)
    orden = [str(CLAUDE), "-p", "--model", MODELO_CHAT, "--tools", "", "--strict-mcp-config",
             "--system-prompt", SISTEMA, "--output-format", "stream-json", "--verbose", "--include-partial-messages",
             "--session-id" if primera else "--resume", sesion]
    mensaje = "Tablero ahora:\n" + json.dumps(foto_para_chat(), ensure_ascii=False) + "\n\nPregunta: " + pregunta
    p = subprocess.Popen(orden, cwd=DIR_CHAT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    reloj = threading.Timer(180, p.kill)
    reloj.start()
    try:
        p.stdin.write(mensaje.encode("utf-8"))
        p.stdin.close()
        hubo = False
        for linea in p.stdout:
            try:
                e = json.loads(linea)
            except ValueError:
                continue
            if e.get("type") == "stream_event":
                delta = e["event"].get("delta", {})
                if delta.get("type") == "text_delta":
                    hubo = True
                    yield delta["text"]
            elif e.get("type") == "result" and (e.get("is_error") or not hubo):
                yield ("\n[Error] " if e.get("is_error") else "") + str(e.get("result") or "Claude no devolvió respuesta.")
                hubo = True
        if not hubo:
            yield "[Error] Claude no respondió. ¿Está abierta la sesión de Claude Code en esta máquina?"
    finally:
        reloj.cancel()
        if p.poll() is None:
            p.kill()


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def responder(self, cuerpo, tipo):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path.startswith("/datos"):
            self.responder(json.dumps(datos(), ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        elif self.path in ("/", "/index.html"):
            self.responder((DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        # Solo JSON: asi otra pagina abierta en el navegador no puede gastar la cuenta mandando un formulario.
        if self.path != "/chat" or "application/json" not in self.headers.get("Content-Type", ""):
            return self.send_error(404)
        try:
            c = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            pregunta, sesion = str(c["pregunta"]).strip()[:2000], str(c["sesion"])
            assert pregunta and UUID.match(sesion)
        except Exception:
            return self.send_error(400)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()   # sin Content-Length: la respuesta va saliendo y termina al cerrar la conexion
        try:
            for pedazo in chat(pregunta, sesion, bool(c.get("primera"))):
                self.wfile.write(pedazo.encode("utf-8"))
                self.wfile.flush()
        except OSError:
            pass   # el navegador cerro la pagina a mitad de la respuesta


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()
