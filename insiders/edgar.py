"""Compras y ventas de directivos de empresas de EE.UU. (Form 4 de la SEC), en una base local.

Cuando un director, un ejecutivo o un accionista de mas del 10% opera acciones de
su empresa tiene que presentar un Form 4 en EDGAR dentro de los 2 dias habiles.
Este modulo los baja, los lee y los guarda en datos/insiders.db:

  - Historia: el indice diario de EDGAR (form.AAAAMMDD.idx) lista todo lo
    presentado cada dia; se publica a la noche. Unos 450 Form 4 por dia.
  - Lo de hoy: el feed de ultimas presentaciones (getcurrent), que cubre los
    ultimos 2 o 3 dias y tapa el hueco hasta que sale el indice.
  - Un emisor puntual: su lista de presentaciones (data.sec.gov/submissions),
    para ver un año entero de un ticker aunque la base cubra menos.

Cada Form 4 es un pedido. La SEC corta a quien pide mas de 10 por segundo y
exige un User-Agent con un mail de contacto: SEC_USER_AGENT en el .env de la raiz.

Cluster = 2 o mas directivos distintos (director u officer) comprando en mercado
abierto (codigo P) la misma accion dentro de la ventana. Los accionistas del 10%
que no son directivos se muestran pero no cuentan: un fondo comprando es otra señal.
Las enmiendas (4/A) se guardan pero no entran en las compras, para no contar dos
veces la misma operacion.

Uso:
    py insiders/edgar.py actualizar [--dias 30]
    py insiders/edgar.py clusters [--dias 14] [--min 2]
    py insiders/edgar.py emisor APLD
"""
import argparse
import json
import msvcrt
import os
import re
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import requests

DIR = Path(__file__).resolve().parent
REPO = DIR.parent
BASE = DIR / "datos" / "insiders.db"
TICKERS = DIR / "datos" / "tickers.json"
SEC = "https://www.sec.gov"
POR_SEGUNDO = 8     # la SEC bloquea por un rato a quien pasa de 10
HILOS = 6
DIAS_HISTORIA = 30
DIAS_EMISOR = 365

# Que significa cada codigo de transaccion del Form 4 (los que aparecen seguido).
CODIGOS = {
    "P": "Compra", "S": "Venta", "A": "Asignación", "M": "Ejercicio", "X": "Ejercicio", "F": "Impuestos",
    "G": "Regalo", "D": "Devolución", "C": "Conversión", "J": "Otra", "W": "Herencia", "I": "Discrecional",
    "V": "Voluntaria", "L": "Chica", "Z": "Fideicomiso", "K": "Swap", "E": "Vencimiento", "H": "Vencimiento",
    "O": "Ejercicio", "U": "Oferta",
}
ESQUEMA = """
CREATE TABLE IF NOT EXISTS presentaciones (
    acc TEXT PRIMARY KEY, presentado TEXT, tipo TEXT, emisor_cik INTEGER, ticker TEXT, emisor TEXT,
    insider_cik INTEGER, insider TEXT, cargo TEXT, director INTEGER, officer INTEGER, diez INTEGER,
    plan INTEGER, error TEXT);
CREATE TABLE IF NOT EXISTS operaciones (
    acc TEXT, n INTEGER, fecha TEXT, codigo TEXT, ad TEXT, acciones REAL, precio REAL, despues REAL,
    directa TEXT, titulo TEXT, PRIMARY KEY (acc, n));
CREATE TABLE IF NOT EXISTS indices (dia TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS emisores (cik INTEGER PRIMARY KEY, revisado TEXT);
CREATE INDEX IF NOT EXISTS pres_emisor ON presentaciones (emisor_cik);
CREATE INDEX IF NOT EXISTS pres_ticker ON presentaciones (ticker);
CREATE INDEX IF NOT EXISTS ops_fecha ON operaciones (fecha, codigo);
"""


def agente():
    """User-Agent para la SEC: del entorno o del .env de la raiz; si no esta, uno generico."""
    if os.getenv("SEC_USER_AGENT"):
        return os.getenv("SEC_USER_AGENT")
    archivo = REPO / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            k, _, v = linea.partition("=")
            if k.strip() == "SEC_USER_AGENT" and v.strip():
                return v.strip().strip('"').strip("'")
    return "ClaudeCodeTest insiders-tracker admin@example.com"


class Ritmo:
    """Reparte los pedidos de todos los hilos para no pasar de n por segundo."""

    def __init__(self, n):
        self.intervalo, self.proximo, self.candado = 1 / n, 0.0, threading.Lock()

    def esperar(self):
        with self.candado:
            ahora = time.monotonic()
            turno = max(ahora, self.proximo)
            self.proximo = turno + self.intervalo
        time.sleep(max(0.0, turno - ahora))


_ritmo = Ritmo(POR_SEGUNDO)
_sesion = requests.Session()
_sesion.headers.update({"User-Agent": agente(), "Accept-Encoding": "gzip, deflate"})


def pedir(url):
    """Texto de la URL; None si no existe (404). Reintenta los cortes y los 429/503."""
    for intento in range(4):
        _ritmo.esperar()
        try:
            r = _sesion.get(url, timeout=30)
        except requests.RequestException:
            if intento == 3:
                raise
            time.sleep(2 ** intento)
            continue
        if r.status_code == 404:
            return None
        if r.status_code in (429, 503) and intento < 3:
            time.sleep(5 * (intento + 1))
            continue
        r.raise_for_status()
        return r.text
    return None


def conectar():
    BASE.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(BASE, timeout=60)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(ESQUEMA)
    return c


# ---------------------------------------------------------------- leer un Form 4

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def limpiar_ticker(t):
    """El ticker tal como lo escribe cada empresa: a veces dos clases juntas ("HEI, HEI.A") o el sufijo OTC ("HBIA.PK")."""
    t = re.split(r"[,;/\s]+", (t or "").strip().upper())[0]
    t = re.sub(r"\.(PK|OB|OTC|QB|QX)$", "", t)
    return "" if t in ("NONE", "N/A", "NA", "-") else t


def leer_form4(texto):
    """De la presentacion completa (.txt) saca el emisor, el insider y las operaciones con acciones."""
    i, j = texto.find("<ownershipDocument"), texto.find("</ownershipDocument>")
    if i < 0 or j < 0:
        raise ValueError("no trae ownershipDocument")
    doc = ET.fromstring(texto[i:j + len("</ownershipDocument>")])
    v = lambda nodo, ruta: (nodo.findtext(ruta) or "").strip() if nodo is not None else ""
    si = lambda x: x.lower() in ("1", "true")

    duenos = doc.findall("reportingOwner")
    if not duenos:
        raise ValueError("sin reportingOwner")
    rels = [d.find("reportingOwnerRelationship") for d in duenos]
    nombre = v(duenos[0], "reportingOwnerId/rptOwnerName")
    if len(duenos) > 1:
        nombre += f" y {len(duenos) - 1} más"
    pres = {
        "tipo": v(doc, "documentType"), "emisor_cik": int(v(doc, "issuer/issuerCik") or 0),
        "ticker": limpiar_ticker(v(doc, "issuer/issuerTradingSymbol")), "emisor": v(doc, "issuer/issuerName"),
        "insider_cik": int(v(duenos[0], "reportingOwnerId/rptOwnerCik") or 0), "insider": nombre,
        "cargo": next((v(r, "officerTitle") for r in rels if v(r, "officerTitle")), ""),
        "director": int(any(si(v(r, "isDirector")) for r in rels)),
        "officer": int(any(si(v(r, "isOfficer")) for r in rels)),
        "diez": int(any(si(v(r, "isTenPercentOwner")) for r in rels)),
        "plan": int(si(v(doc, "aff10b5One"))),
    }
    ops = []
    for t in doc.iterfind("nonDerivativeTable/nonDerivativeTransaction"):
        ops.append({
            "fecha": v(t, "transactionDate/value")[:10], "codigo": v(t, "transactionCoding/transactionCode"),
            "ad": v(t, "transactionAmounts/transactionAcquiredDisposedCode/value"),
            "acciones": num(v(t, "transactionAmounts/transactionShares/value")),
            "precio": num(v(t, "transactionAmounts/transactionPricePerShare/value")),
            "despues": num(v(t, "postTransactionAmounts/sharesOwnedFollowingTransaction/value")),
            "directa": v(t, "ownershipNature/directOrIndirectOwnership/value"),
            "titulo": v(t, "securityTitle/value"),
        })
    return pres, ops


def guardar(c, acc, presentado, pres=None, ops=(), error=None):
    p = pres or {}
    c.execute("INSERT OR REPLACE INTO presentaciones VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        acc, presentado, p.get("tipo"), p.get("emisor_cik"), p.get("ticker"), p.get("emisor"), p.get("insider_cik"),
        p.get("insider"), p.get("cargo"), p.get("director"), p.get("officer"), p.get("diez"), p.get("plan"), error))
    c.execute("DELETE FROM operaciones WHERE acc = ?", (acc,))
    c.executemany("INSERT INTO operaciones VALUES (?,?,?,?,?,?,?,?,?,?)", [
        (acc, n, o["fecha"], o["codigo"], o["ad"], o["acciones"], o["precio"], o["despues"], o["directa"], o["titulo"])
        for n, o in enumerate(ops)])


def bajar(c, pendientes, avance=None, que=""):
    """Baja y guarda cada presentacion de pendientes {acc: (url, presentado)}. Devuelve cuantas fallaron por red."""
    ya = {r[0] for r in c.execute("SELECT acc FROM presentaciones")}
    faltan = {a: x for a, x in pendientes.items() if a not in ya}
    fallas = 0

    def una(acc, url):
        texto = pedir(url)
        if texto is None:
            return acc, None, None, "no existe"
        try:
            pres, ops = leer_form4(texto)
            return acc, pres, ops, None
        except (ValueError, ET.ParseError) as e:
            return acc, None, (), f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(HILOS) as ex:
        futuros = {ex.submit(una, a, u): (a, p) for a, (u, p) in faltan.items()}
        for k, f in enumerate(as_completed(futuros), 1):
            acc, presentado = futuros[f]
            try:
                _, pres, ops, error = f.result()
            except requests.RequestException:
                fallas += 1   # sin guardar: se reintenta en la proxima vuelta
            else:
                guardar(c, acc, presentado, pres, ops or (), error)
            if k % 25 == 0:
                c.commit()
            if avance:
                avance(que, k, len(faltan))
    c.commit()
    return fallas


# ---------------------------------------------------------------- de donde salen

def trimestres(desde, hasta):
    a, t = desde.year, (desde.month - 1) // 3 + 1
    while (a, t) <= (hasta.year, (hasta.month - 1) // 3 + 1):
        yield a, t
        a, t = (a, t + 1) if t < 4 else (a + 1, 1)


def indices_publicados(desde):
    """Dias con indice diario publicado desde la fecha dada, del mas nuevo al mas viejo."""
    dias = []
    for a, t in trimestres(desde, date.today()):
        texto = pedir(f"{SEC}/Archives/edgar/daily-index/{a}/QTR{t}/index.json")
        if not texto:
            continue
        for item in json.loads(texto)["directory"]["item"]:
            m = re.fullmatch(r"form\.(\d{8})\.idx", item["name"])
            if m:
                d = date(int(m[1][:4]), int(m[1][4:6]), int(m[1][6:]))
                if d >= desde:
                    dias.append((d, f"{SEC}/Archives/edgar/daily-index/{a}/QTR{t}/{item['name']}"))
    return sorted(dias, reverse=True)


def form4_del_indice(url):
    """{acc: (url del .txt, fecha)} de los Form 4 de un indice diario. Cada uno figura una vez por CIK."""
    texto = pedir(url) or ""
    salida = {}
    for linea in texto.splitlines():
        partes = linea.split()
        if len(partes) >= 4 and partes[0] in ("4", "4/A") and partes[-1].endswith(".txt"):
            acc = partes[-1].rsplit("/", 1)[1][:-4]
            f = partes[-2]
            salida[acc] = (f"{SEC}/Archives/{partes[-1]}", f"{f[:4]}-{f[4:6]}-{f[6:]}")
    return salida


def form4_recientes(hasta_dia):
    """Form 4 del feed de ultimas presentaciones, desde ahora hasta el dia dado (o lo que alcance el feed)."""
    salida = {}
    for inicio in range(0, 2000, 100):
        texto = pedir(f"{SEC}/cgi-bin/browse-edgar?action=getcurrent&type=4&owner=only"
                      f"&count=100&start={inicio}&output=atom") or ""
        entradas = re.findall(r"<entry>.*?</entry>", texto, re.S)
        if not entradas:
            break
        viejo = False
        for e in entradas:
            forma = re.search(r'term="([^"]+)"', e)
            acc = re.search(r"accession-number=([\d-]+)", e)
            cik = re.search(r"/edgar/data/(\d+)/", e)
            fecha = re.search(r"Filed:&lt;/b&gt; (\d{4}-\d{2}-\d{2})", e)
            if not (forma and acc and cik and fecha):
                continue
            if fecha[1] < hasta_dia:
                viejo = True
            elif forma[1] in ("4", "4/A"):
                salida[acc[1]] = (f"{SEC}/Archives/edgar/data/{cik[1]}/{acc[1]}.txt", fecha[1])
        if viejo:
            break
    return salida


class Ocupado(Exception):
    """Otro proceso (el servidor o la linea de comandos) ya esta bajando."""


def actualizar(dias=DIAS_HISTORIA, avance=None):
    """Completa la base: primero lo de hoy y despues los indices diarios que falten, de lo nuevo a lo viejo.

    Un solo proceso por vez: dos bajando juntos pasarian el limite de la SEC.
    """
    BASE.parent.mkdir(exist_ok=True)
    traba = open(BASE.parent / "actualizando.lock", "a+b")
    try:
        traba.seek(0)
        msvcrt.locking(traba.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        traba.close()
        raise Ocupado("ya hay otra actualización en curso")
    try:
        return _actualizar(dias, avance)
    finally:
        traba.seek(0)
        msvcrt.locking(traba.fileno(), msvcrt.LK_UNLCK, 1)
        traba.close()


def _actualizar(dias, avance):
    c = conectar()
    try:
        desde = date.today() - timedelta(days=dias)
        hechos = {r[0] for r in c.execute("SELECT dia FROM indices")}
        publicados = indices_publicados(desde)
        ultimo = publicados[0][0] if publicados else desde
        if avance:
            avance("presentaciones de hoy", 0, 0)
        fallas = bajar(c, form4_recientes(ultimo.isoformat()), avance, "presentaciones de hoy")
        for d, url in publicados:
            if d.isoformat() in hechos:
                continue
            que = f"índice del {d:%d-%m}"
            if avance:
                avance(que, 0, 0)
            if bajar(c, form4_del_indice(url), avance, que) == 0:
                c.execute("INSERT OR IGNORE INTO indices VALUES (?)", (d.isoformat(),))
                c.commit()
            else:
                fallas += 1
        return fallas
    finally:
        c.close()


# ---------------------------------------------------------------- un emisor puntual

def cik_de(ticker):
    """CIK del emisor de un ticker: primero la base, despues la lista de la SEC (se baja una vez por semana)."""
    ticker = ticker.upper()
    c = conectar()
    try:
        r = c.execute("SELECT emisor_cik FROM presentaciones WHERE ticker = ? AND emisor_cik > 0 "
                      "ORDER BY presentado DESC LIMIT 1", (ticker,)).fetchone()
    finally:
        c.close()
    if r:
        return r[0]
    if not TICKERS.exists() or time.time() - TICKERS.stat().st_mtime > 7 * 86400:
        texto = pedir(f"{SEC}/files/company_tickers.json")
        if texto:
            TICKERS.parent.mkdir(exist_ok=True)
            TICKERS.write_text(texto, encoding="utf-8")
    if not TICKERS.exists():
        return None
    for x in json.loads(TICKERS.read_text(encoding="utf-8")).values():
        if x["ticker"].upper() == ticker:
            return int(x["cik_str"])
    return None


def historial_emisor(cik, dias=DIAS_EMISOR, avance=None):
    """Baja los Form 4 del ultimo año de un emisor (una vez por dia como mucho)."""
    c = conectar()
    try:
        hoy = date.today().isoformat()
        r = c.execute("SELECT revisado FROM emisores WHERE cik = ?", (cik,)).fetchone()
        if r and r[0] == hoy:
            return 0
        texto = pedir(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
        if not texto:
            return 0
        rec = json.loads(texto)["filings"]["recent"]
        desde = (date.today() - timedelta(days=dias)).isoformat()
        pendientes = {
            acc: (f"{SEC}/Archives/edgar/data/{cik}/{acc}.txt", f)
            for forma, f, acc in zip(rec["form"], rec["filingDate"], rec["accessionNumber"])
            if forma in ("4", "4/A") and f >= desde
        }
        fallas = bajar(c, pendientes, avance, "historial del emisor")
        if fallas == 0:
            c.execute("INSERT OR REPLACE INTO emisores VALUES (?, ?)", (cik, hoy))
            c.commit()
        return fallas
    finally:
        c.close()


# ---------------------------------------------------------------- consultas

def es_alto(cargo):
    return bool(re.search(r"\b(ceo|cfo|coo|chief|president|chair)", cargo or "", re.I))


def rol(p):
    """Rol corto para mostrar: el cargo si es officer, si no director o 10%."""
    partes = []
    if p["officer"] and p["cargo"]:
        partes.append(p["cargo"])
    elif p["officer"]:
        partes.append("Officer")
    if p["director"]:
        partes.append("Director")
    if p["diez"]:
        partes.append("10%")
    return " · ".join(partes) or "Otro"


def por_presentacion(filas):
    """Junta las lineas de una misma presentacion y codigo (un Form 4 suele traer varias compras a distinto precio)."""
    grupos = {}
    for f in filas:
        g = grupos.setdefault((f["acc"], f["codigo"]), {
            "acc": f["acc"], "presentado": f["presentado"], "ticker": limpiar_ticker(f["ticker"]), "emisor": f["emisor"],
            "emisorCik": f["emisor_cik"], "insiderCik": f["insider_cik"], "insider": f["insider"],
            "rol": rol(f), "directivo": bool(f["director"] or f["officer"]), "alto": es_alto(f["cargo"]),
            "diez": bool(f["diez"]), "plan": bool(f["plan"]), "codigo": f["codigo"],
            "tipo": CODIGOS.get(f["codigo"], f["codigo"]), "desde": f["fecha"], "hasta": f["fecha"],
            "acciones": 0.0, "valor": 0.0, "despues": None,
        })
        g["desde"], g["hasta"] = min(g["desde"], f["fecha"]), max(g["hasta"], f["fecha"])
        signo = -1 if f["ad"] == "D" else 1
        g["acciones"] += signo * (f["acciones"] or 0)
        g["valor"] += signo * (f["acciones"] or 0) * (f["precio"] or 0)
        if f["despues"] is not None:
            g["despues"] = f["despues"]
    for g in grupos.values():
        g["precio"] = round(g["valor"] / g["acciones"], 4) if g["acciones"] and g["valor"] else None
        # Cuanto agrando (o achico) su tenencia: lo operado contra lo que tenia antes.
        antes = (g["despues"] or 0) - g["acciones"]
        g["cambioTenencia"] = round(g["acciones"] / antes * 100, 1) if antes > 0 else None
    return sorted(grupos.values(), key=lambda g: (g["hasta"], g["presentado"]), reverse=True)


CONSULTA = """
SELECT o.*, p.presentado, p.tipo, p.emisor_cik, p.ticker, p.emisor, p.insider_cik, p.insider, p.cargo,
       p.director, p.officer, p.diez, p.plan
FROM operaciones o JOIN presentaciones p USING (acc)
"""


def compras(dias=14):
    """Compras en mercado abierto (codigo P) hechas en los ultimos dias, una fila por presentacion."""
    desde = (date.today() - timedelta(days=dias)).isoformat()
    c = conectar()
    try:
        filas = c.execute(CONSULTA + " WHERE o.codigo = 'P' AND o.ad = 'A' AND p.tipo = '4' AND o.fecha >= ? "
                          "AND o.precio > 0 AND p.ticker != ''", (desde,)).fetchall()
    finally:
        c.close()
    return por_presentacion(filas)


def clusters(dias=14, minimo=2):
    """Acciones donde compraron al menos `minimo` directivos distintos dentro de la ventana."""
    grupos = {}
    for g in compras(dias):
        grupos.setdefault(g["emisorCik"], []).append(g)
    salida = []
    for cik, gs in grupos.items():
        directivos = {g["insiderCik"] for g in gs if g["directivo"]}
        if len(directivos) < minimo:
            continue
        acciones = sum(g["acciones"] for g in gs)
        valor = sum(g["valor"] for g in gs)
        # Varios insiders el mismo dia al mismo precio exacto no es una compra en pantalla: es un plan de
        # compra para empleados, un DRIP o la suscripcion de una colocacion (TSM con 33 "directivos" a 79,39).
        mismo = {}
        for g in gs:
            mismo.setdefault((g["hasta"], round(g["precio"] or 0, 2)), set()).add(g["insiderCik"])
        salida.append({
            "mismoPrecio": max(len(s) for s in mismo.values()),
            "ticker": gs[0]["ticker"], "emisor": gs[0]["emisor"], "emisorCik": cik,
            "directivos": len(directivos), "compras": len(gs), "valor": round(valor),
            "precio": round(valor / acciones, 4) if acciones else None,
            "desde": min(g["desde"] for g in gs), "hasta": max(g["hasta"] for g in gs),
            "presentado": max(g["presentado"] for g in gs),
            "alto": any(g["alto"] for g in gs), "plan": sum(g["plan"] for g in gs),
            "insiders": [{k: g[k] for k in ("insider", "rol", "directivo", "valor", "precio", "hasta", "plan", "cambioTenencia")}
                         for g in sorted(gs, key=lambda g: -g["valor"])],
        })
    return sorted(salida, key=lambda s: -s["valor"])


def operaciones_emisor(cik, dias=DIAS_EMISOR):
    """Todas las operaciones con acciones de un emisor en el periodo, una fila por presentacion y codigo."""
    desde = (date.today() - timedelta(days=dias)).isoformat()
    c = conectar()
    try:
        filas = c.execute(CONSULTA + " WHERE p.emisor_cik = ? AND o.fecha >= ? AND p.tipo = '4'",
                          (cik, desde)).fetchall()
    finally:
        c.close()
    return por_presentacion(filas)


def cobertura():
    """Que dias tiene la base y cuantas presentaciones."""
    c = conectar()
    try:
        r = c.execute("SELECT MIN(dia), MAX(dia), COUNT(*) FROM indices").fetchone()
        n = c.execute("SELECT COUNT(*), MAX(presentado) FROM presentaciones").fetchone()
        return {"desde": r[0], "hasta": r[1], "indices": r[2], "presentaciones": n[0], "ultimaPresentacion": n[1]}
    finally:
        c.close()


def mostrar_avance(que, k, total):
    if total and (k == total or k % 50 == 0):
        print(f"  {que}: {k}/{total}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="orden", required=True)
    a = sub.add_parser("actualizar")
    a.add_argument("--dias", type=int, default=DIAS_HISTORIA)
    a = sub.add_parser("clusters")
    a.add_argument("--dias", type=int, default=14)
    a.add_argument("--min", type=int, default=2)
    a = sub.add_parser("emisor")
    a.add_argument("ticker")
    x = ap.parse_args()

    if x.orden == "actualizar":
        t0 = time.time()
        try:
            fallas = actualizar(x.dias, mostrar_avance)
        except Ocupado as e:
            raise SystemExit(f"No actualizo: {e} (¿está abierto el tablero?)")
        print(f"listo en {time.time() - t0:.0f} s; fallas de red: {fallas}; base: {cobertura()}")
    elif x.orden == "clusters":
        for s in clusters(x.dias, x.min):
            print(f"{s['ticker']:<6} {s['directivos']} directivos  US$ {s['valor']:>13,.0f}  "
                  f"{s['desde']} a {s['hasta']}  {s['emisor']}")
            for i in s["insiders"]:
                print(f"         {i['insider']:<32} {i['rol'][:40]:<40} US$ {i['valor']:>12,.0f} a {i['precio']}")
    else:
        cik = cik_de(x.ticker)
        if not cik:
            raise SystemExit(f"No encuentro el CIK de {x.ticker}")
        historial_emisor(cik, avance=mostrar_avance)
        for g in operaciones_emisor(cik):
            print(f"{g['hasta']} {g['tipo']:<11} {g['insider'][:28]:<28} {g['rol'][:30]:<30} "
                  f"{g['acciones']:>12,.0f} a {g['precio'] or 0:>9.2f}  US$ {g['valor']:>13,.0f}")
