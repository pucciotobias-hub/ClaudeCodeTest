"""Carga en el JSON del reporte semanal las velas diarias de GGAL, leidas del chart.

Por que existe (2026-11-17): el 16-nov la corrida dejo "velas": "__VELAS__" en el
JSON, un marcador que nunca reemplazo, y la pagina salio sin grafico. Copiar a mano
100 filas de data_get_ohlcv es justo el paso que se saltea; este script las lee
directo del chart (TradingView en Chrome con CDP en el puerto 9222) y las escribe.

El chart tiene que estar en GGAL diario: si no, aborta sin tocar el JSON.

Uso:
    py scripts/ggal_semanal_velas.py estudios/ggal/semanal/<FECHA>.json <VIERNES AAAA-MM-DD>
"""
import asyncio
import datetime
import json
import pathlib
import sys
import urllib.request

import websockets

CDP = "http://127.0.0.1:9222/json"
CANTIDAD = 100
JS = """(()=>{const s=TradingViewApi._activeChartWidgetWV.value()._chartWidget.model().mainSeries();
const b=s.bars(),o=[];for(let i=b.firstIndex();i<=b.lastIndex();i++){const v=b.valueAt(i);if(v)o.push(v);}
return JSON.stringify({sym:s.symbol(),res:s.interval(),bars:o});})()"""


async def leer_chart():
    pestanas = json.load(urllib.request.urlopen(CDP, timeout=10))
    tv = [t for t in pestanas if t.get("type") == "page" and "tradingview.com/chart" in t.get("url", "")]
    if not tv:
        raise SystemExit("No hay una pestaña de TradingView con CDP: no se toca el JSON.")
    async with websockets.connect(tv[0]["webSocketDebuggerUrl"], max_size=None) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                  "params": {"expression": JS, "returnByValue": True}}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 1:
                return json.loads(r["result"]["result"]["value"])


def main():
    ruta, viernes = pathlib.Path(sys.argv[1]), sys.argv[2]
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    d = asyncio.run(leer_chart())
    if not d["sym"].endswith("GGAL") or d["res"] not in ("1D", "D"):
        raise SystemExit(f"El chart esta en {d['sym']} {d['res']}, no en GGAL diario: no se toca el JSON.")
    filas = []
    for v in d["bars"]:
        fecha = datetime.datetime.fromtimestamp(v[0], datetime.timezone.utc).strftime("%Y-%m-%d")
        if fecha <= viernes and v[5] is not None:
            filas.append([fecha] + [round(x, 4) for x in v[1:5]] + [int(v[5])])
    filas = filas[-CANTIDAD:]
    if len(filas) < 30 or filas[-1][0] != viernes:
        raise SystemExit(f"Velas incompletas ({len(filas)}, ultima {filas[-1][0] if filas else '-'}): no se toca el JSON.")
    datos["velas"] = filas
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok: {len(filas)} velas, {filas[0][0]} a {filas[-1][0]} (cierre {filas[-1][4]})")


if __name__ == "__main__":
    main()
