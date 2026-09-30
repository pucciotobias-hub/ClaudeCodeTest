"""Servidor local de la oficina 3D de los agentes GGAL.

Sirve la escena (index.html) y un endpoint /estado que dice quien esta
trabajando. El estado lo escribe scripts/ggal_estudio.ps1 en oficina/estado.json
al arrancar, en cada paso y al terminar; aca se valida contra el PID del wrapper
para que una corrida que murio sin avisar no deje al personaje trabajando para
siempre. Del log se sacan las ultimas corridas de cada turno.

Uso:  pythonw oficina/servidor.py      (lo levanta solo abrir_oficina.ps1)
"""
import ctypes
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUERTO = 8765
DIR = Path(__file__).resolve().parent
ESTADO = DIR / "estado.json"
LOG = DIR.parent / "logs" / "ggal_estudio.log"

# Cuando fue la ultima vez que una pestania pidio el estado: el wrapper lo usa
# para no abrir otra si ya hay una mirando.
ultimo_sondeo = 0.0

LINEA = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (\w+)\s*\| (.*)$")


def pid_vivo(pid):
    if not pid:
        return False
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    codigo = ctypes.c_ulong()
    ok = k32.GetExitCodeProcess(h, ctypes.byref(codigo))
    k32.CloseHandle(h)
    return bool(ok) and codigo.value == 259  # STILL_ACTIVE


def leer_estado():
    try:
        e = json.loads(ESTADO.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {"activo": False}
    if e.get("activo") and not pid_vivo(e.get("pid")):
        e["activo"] = False
        e["resultado"] = "murio"
    return e


def ultimas_corridas():
    """Ultimo resultado de cada turno segun el log del wrapper."""
    try:
        lineas = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-600:]
    except OSError:
        return {}
    turnos, anterior, actual = {}, {}, None
    for l in lineas:
        m = LINEA.match(l)
        if not m:
            continue
        cuando, nivel, msg = m.groups()
        t = re.search(r"INICIO estudio GGAL - turno: (\w+)", msg)
        if t:
            actual = t.group(1)
            anterior[actual] = turnos.get(actual)
            turnos[actual] = {"inicio": cuando, "resultado": "sin cerrar"}
            continue
        if not actual:
            continue
        if "Nada que hacer" in msg or "Se saltea" in msg:
            # Un reintento que no tenia nada que hacer no tapa la corrida de verdad.
            turnos[actual] = anterior[actual] or {"inicio": cuando, "resultado": "salteado"}
        elif msg.startswith("OK."):
            turnos[actual].update(resultado="ok", fin=cuando)
        elif nivel == "ERROR":
            turnos[actual].update(resultado="error", fin=cuando)
    return turnos


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
        global ultimo_sondeo
        ruta = self.path.split("?")[0]
        if ruta == "/estado":
            ultimo_sondeo = time.time()
            cuerpo = {"estado": leer_estado(), "corridas": ultimas_corridas(), "ahora": time.strftime("%Y-%m-%d %H:%M:%S")}
            self.responder(json.dumps(cuerpo, ensure_ascii=False), "application/json; charset=utf-8")
        elif ruta == "/mirando":
            self.responder(json.dumps({"mirando": time.time() - ultimo_sondeo < 10}), "application/json")
        elif ruta in ("/", "/index.html"):
            self.responder((DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_error(404)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()
