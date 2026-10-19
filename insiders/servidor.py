"""Tablero de compras de directivos (insider tracker) sobre los Form 4 de la SEC.

Los datos de las operaciones salen de edgar.py (base local datos/insiders.db). El
servidor la mantiene al dia en segundo plano: al arrancar y despues cada 20
minutos baja lo que falte. Los precios salen de yfinance: el ultimo cierre de
cada accion con compras (para ver como le va al que compro) y un año de cierres
diarios para el grafico de cada ticker.

Uso:  pythonw insiders/servidor.py      (lo levanta solo abrir_insiders.ps1)
"""
import json
import os
import sys
import threading
import time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import yfinance as yf

import edgar

# pythonw no tiene consola: sin esto un print de una libreria corta el hilo.
if sys.stdout is None or sys.stderr is None:
    sys.stdout = sys.stderr = open(os.devnull, "w")

PUERTO = 8769
DIR = Path(__file__).resolve().parent
CADA_SEG = 20 * 60          # cada cuanto buscar presentaciones nuevas
VIGENCIA_PRECIO = 10 * 60   # no pedirle a yfinance el mismo precio mas de una vez cada 10 minutos
VIGENCIA_FICHA = 10 * 60

estado = {"corriendo": False, "que": "", "hechos": 0, "total": 0, "ultima": None, "error": None, "fallas": 0}
_despertar = threading.Event()
_precios = {}           # ticker -> (precio, cuando)
_fichas = {}            # ticker -> (datos, cuando)
_candado_precios = threading.Lock()
_candado_fichas = {}    # ticker -> Lock: dos pedidos del mismo ticker esperan al primero


def avance(que, k, total):
    estado.update(que=que, hechos=k, total=total)


def actualizador():
    """Mantiene la base al dia. Se despierta antes si la pagina pide actualizar."""
    while True:
        estado.update(corriendo=True, error=None)
        espera = CADA_SEG
        try:
            estado["fallas"] = edgar.actualizar(avance=avance)
            estado["ultima"] = datetime.now().isoformat(timespec="seconds")
        except edgar.Ocupado as e:   # la linea de comandos esta bajando: volver a mirar en un minuto
            estado["error"] = str(e)
            espera = 60
        except Exception as e:   # sin red o la SEC caida: probar en la proxima vuelta
            estado["error"] = f"{type(e).__name__}: {e}"
        estado.update(corriendo=False, que="", hechos=0, total=0)
        _despertar.wait(espera)
        _despertar.clear()


def para_yf(ticker):
    return ticker.replace(".", "-")   # BRK.B en la SEC es BRK-B en Yahoo


def precios(tickers):
    """Ultimo precio de cada ticker (None si yfinance no lo conoce)."""
    with _candado_precios:
        ahora = time.time()
        falta = sorted({t for t in tickers if t not in _precios or ahora - _precios[t][1] > VIGENCIA_PRECIO})
        if falta:
            try:
                d = yf.download([para_yf(t) for t in falta], period="5d", interval="1d", progress=False,
                                auto_adjust=False, threads=True)["Close"]
                if isinstance(d, pd.Series):
                    d = d.to_frame(para_yf(falta[0]))
                for t in falta:
                    s = d[para_yf(t)].dropna() if para_yf(t) in d else pd.Series(dtype=float)
                    _precios[t] = (round(float(s.iloc[-1]), 4) if len(s) else None, ahora)
            except Exception:
                for t in falta:
                    _precios.setdefault(t, (None, 0))
        return {t: _precios.get(t, (None, 0))[0] for t in tickers}


def con_precio(filas):
    """Agrega el precio de hoy y cuanto cambio desde el precio promedio de compra.

    Si la relacion es absurda, lo comprado no es lo que cotiza con ese ticker (la accion local de
    un ADR, otra clase): se deja sin comparar en vez de mostrar un +400%.
    """
    hoy = precios([f["ticker"] for f in filas])
    for f in filas:
        f["precioHoy"] = hoy.get(f["ticker"])
        relacion = f["precioHoy"] / f["precio"] if f["precioHoy"] and f["precio"] else None
        f["comparable"] = relacion is None or 0.4 <= relacion <= 2.5
        f["desdeCompra"] = round((relacion - 1) * 100, 1) if relacion and f["comparable"] else None
    return filas


def ficha(ticker):
    """Todo lo de un ticker: datos de la empresa, un año de precios y las operaciones de sus directivos."""
    ticker = ticker.upper()
    candado = _candado_fichas.setdefault(ticker, threading.Lock())
    with candado:
        guardada = _fichas.get(ticker)
        if guardada and time.time() - guardada[1] < VIGENCIA_FICHA:
            return guardada[0]
        cik = edgar.cik_de(ticker)
        if not cik:
            return {"error": f"No encuentro {ticker} en la lista de la SEC."}
        aviso = None
        try:
            if edgar.historial_emisor(cik):
                aviso = "Faltaron algunas presentaciones por cortes de red; recargá en un rato."
        except Exception as e:
            aviso = f"No pude bajar el historial de la SEC ({type(e).__name__}); muestro lo que hay en la base."
        ops = edgar.operaciones_emisor(cik)

        t = yf.Ticker(para_yf(ticker))
        try:
            h = t.history(period="1y", interval="1d", auto_adjust=False)
        except Exception:
            h = pd.DataFrame()
        try:
            info = t.info or {}
        except Exception:
            info = {}
        serie = [{"f": i.date().isoformat(), "c": round(float(c), 4)} for i, c in h.Close.items()] if not h.empty else []

        hace90 = (date.today() - timedelta(days=90)).isoformat()
        recientes = [g for g in ops if g["hasta"] >= hace90]
        compras = [g for g in recientes if g["codigo"] == "P"]
        ventas = [g for g in recientes if g["codigo"] == "S"]
        precio = serie[-1]["c"] if serie else None
        datos = {
            "ticker": ticker, "cik": cik,
            "emisor": info.get("longName") or (ops[0]["emisor"] if ops else ticker),
            "sector": info.get("sector"), "industria": info.get("industry"), "bolsa": info.get("exchange"),
            "capitalizacion": info.get("marketCap"), "pe": info.get("trailingPE"), "peFuturo": info.get("forwardPE"),
            "precio": precio,
            "var": round((serie[-1]["c"] / serie[-2]["c"] - 1) * 100, 2) if len(serie) > 1 else None,
            "max52": max((p["c"] for p in serie), default=None), "min52": min((p["c"] for p in serie), default=None),
            "serie": serie, "operaciones": ops, "aviso": aviso,
            "resumen90": {
                "compras": round(sum(g["valor"] for g in compras)), "ventas": round(-sum(g["valor"] for g in ventas)),
                "compradores": len({g["insiderCik"] for g in compras}), "vendedores": len({g["insiderCik"] for g in ventas}),
            },
        }
        _fichas[ticker] = (datos, time.time())
        return datos


def numero(q, clave, defecto, minimo, maximo):
    try:
        return max(minimo, min(maximo, int(q.get(clave, [defecto])[0])))
    except ValueError:
        return defecto


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def responder(self, cuerpo, tipo="application/json; charset=utf-8"):
        if not isinstance(cuerpo, bytes):
            cuerpo = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                self.responder((DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif u.path == "/estado":
                self.responder({**estado, "base": edgar.cobertura()})
            elif u.path == "/clusters":
                dias, minimo = numero(q, "dias", 14, 1, 90), numero(q, "min", 2, 2, 10)
                self.responder({"dias": dias, "min": minimo, "clusters": con_precio(edgar.clusters(dias, minimo))})
            elif u.path == "/compras":
                dias = numero(q, "dias", 14, 1, 90)
                self.responder({"dias": dias, "compras": con_precio(edgar.compras(dias))})
            elif u.path.startswith("/ticker/"):
                ticker = u.path.split("/", 2)[2].strip().upper()
                if not ticker or len(ticker) > 10 or not ticker.replace(".", "").replace("-", "").isalnum():
                    return self.send_error(400)
                self.responder(ficha(ticker))
            else:
                self.send_error(404)
        except OSError:
            pass   # el navegador cerro la conexion
        except Exception as e:
            self.responder({"error": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        if self.path != "/actualizar" or "application/json" not in self.headers.get("Content-Type", ""):
            return self.send_error(404)
        _despertar.set()
        self.responder({"ok": True})


if __name__ == "__main__":
    threading.Thread(target=actualizador, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()
