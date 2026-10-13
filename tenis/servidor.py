"""Servidor local del juego de tenis.

Sirve la carpeta del script (index.html y los modulos de js/) sin cache, para
que un cambio en el codigo se vea con solo recargar. /vivo le dice al lanzador
que el servidor esta arriba.

Uso:  pythonw tenis/servidor.py      (lo levanta solo abrir_tenis.ps1)
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUERTO = 8768
DIR = Path(__file__).resolve().parent


class Manejador(SimpleHTTPRequestHandler):
    # El registro de Windows a veces devuelve otro tipo para .js y los modulos ES no cargan.
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript"}

    def log_message(self, *a):
        pass  # corre con pythonw, sin consola

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/vivo":
            cuerpo = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        super().do_GET()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PUERTO), partial(Manejador, directory=str(DIR))).serve_forever()
