"""Vigia de las señales de GGAL: avisa cada cambio de postura de la estrategia.

La estrategia `pine/ggal_senales.pine` corre adentro de TradingView y en cada
vela de 15 minutos tiene una postura: LONG, SHORT o AFUERA, con tamaño, stop,
objetivo y R:R. Las alertas de TradingView para estrategias son pagas (el plan
actual tiene 0 alertas tecnicas), asi que este script hace de alerta: lee la
postura del chart por CDP cada minuto durante la rueda y, cuando cambia:

  - avisa con una notificacion de Windows (y por Telegram si hay
    TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID en el .env);
  - lo anota en senales/ggal/<AAAA-MM>.csv;
  - al terminar la rueda commitea y pushea ese CSV, para poder medir la
    estrategia en vivo.

Lee lo mismo que se ve en el chart: la postura vigente que expone la estrategia
(plots p_*: lado, hora, precio, stop, objetivo, R:R, tamaño) y las operaciones
cerradas del reporte del Strategy Tester. Avisa solo cambios de postura de los
ultimos minutos, asi que recalcular el script no dispara avisos viejos. Al
arrancar avisa una vez la postura vigente. No calcula señales por su cuenta.

Convive con el estudio diario: mientras `logs/estudio.lock` existe (lo crea
ggal_estudio.ps1) no toca el chart, y cuando el estudio termina lo vuelve a
poner en GGAL 15m.

Uso:
    python scripts/ggal_senales_vigia.py            # corre la rueda de hoy
    python scripts/ggal_senales_vigia.py --una-vez  # una sola lectura y sale (para probar)
"""
import argparse
import csv
import ctypes
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import websocket

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs"
ESTADO = LOG_DIR / "ggal_senales_estado.json"
LOCK_ESTUDIO = LOG_DIR / "estudio.lock"
DIARIO_DIR = REPO / "senales" / "ggal"
CDP = "http://127.0.0.1:9222"
NY = ZoneInfo("America/New_York")

DESDE = (9, 40)        # hora NY en que empieza a mirar (la primera entrada posible es 9:45)
HASTA = (16, 5)        # hora NY en que deja de mirar (todo cierra en la vela de 15:45)
CADA_SEG = 60
LOCK_VIEJO_MIN = 60    # un lock mas viejo que esto es de una corrida que murio
DATOS_VIEJOS_MIN = 20  # sin velas nuevas en este lapso con la rueda abierta -> reload
RECIENTE_MIN = 45      # un cambio de postura mas viejo que esto no se avisa: es historia

log = logging.getLogger("vigia")

# Todo lo que se lee del chart sale de este JS: la postura vigente (los plots
# p_* de la estrategia en la ultima vela) y las ultimas operaciones cerradas.
# No usa las etiquetas: cambian cada vez que el script se recalcula, y leerlas
# como eventos manda avisos viejos (paso el 2026-09-24 al recompilar: ~23 avisos).
JS_LECTURA = r"""
(() => {
  const c = TradingViewApi.activeChart();
  const model = c._chartWidget.model();
  const s = model.model().dataSources().find(d => {
    try { return (d.metaInfo().description || '').includes('GGAL Se'); } catch (e) { return false; }
  });
  const bars = model.mainSeries().bars();
  const ultima = bars.size() ? bars.valueAt(bars.lastIndex())[0] * 1000 : null;
  const base = { simbolo: c.symbol(), resolucion: c.resolution(), ultimaVela: ultima };
  if (!s) return JSON.stringify(Object.assign(base, { estrategia: false }));
  const meta = s.metaInfo();
  const titulos = (meta.plots || []).map(p => (meta.styles[p.id] && meta.styles[p.id].title) || p.id);
  const fila = s.data().last();
  const p = {};
  if (fila) titulos.forEach((t, i) => { p[t] = fila.value[i + 1]; });
  let r = s._reportData;
  if (r && typeof r.value === 'function') r = r.value();
  const cerradas = ((r && r.trades) || []).filter(t => t.x.c).slice(-5).map(t => ({
    lado: t.e.c.split(' ')[0], tam: t.e.c.split(' ')[1] || '', entrada: t.e.p, tEntrada: t.e.tm,
    salida: t.x.p, tSalida: t.x.tm, motivo: t.x.c, pnl: t.tp.v
  }));
  return JSON.stringify(Object.assign(base, {
    estrategia: true,
    postura: p.postura, hora: p.p_hora, precio: p.p_precio, sl: p.p_sl, tp: p.p_tp, rr: p.p_rr, grande: p.p_grande,
    cerradas: cerradas
  }));
})()
"""


# --- CDP ----------------------------------------------------------------------------
def _target_ws() -> str:
    targets = requests.get(f"{CDP}/json", timeout=5).json()
    for t in targets:
        if t.get("type") == "page" and "tradingview.com/chart" in t.get("url", ""):
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No hay una pestaña de chart de TradingView abierta en el Chrome con CDP.")


def evaluar(expr: str):
    ws = websocket.create_connection(_target_ws(), timeout=20, suppress_origin=True)
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                            "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                break
    finally:
        ws.close()
    res = msg.get("result", {})
    if "exceptionDetails" in res:
        raise RuntimeError(res["exceptionDetails"].get("text", "error de JS"))
    return res.get("result", {}).get("value")


# --- Avisos -------------------------------------------------------------------------
def cargar_env() -> None:
    for ruta in (REPO / ".env", REPO / "quant_bot" / ".env"):
        if not ruta.exists():
            continue
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, _, v = linea.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def notificar(titulo: str, texto: str) -> None:
    log.info("AVISO | %s | %s", titulo, texto.replace("\n", " / "))
    # Notificacion de Windows por PowerShell, sin dependencias. Los textos van por
    # variables de entorno para no pelear con el quoting.
    ps = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;"
        "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        "$t=$x.GetElementsByTagName('text');"
        "$t.Item(0).AppendChild($x.CreateTextNode($env:VIGIA_TITULO))|Out-Null;"
        "$t.Item(1).AppendChild($x.CreateTextNode($env:VIGIA_TEXTO))|Out-Null;"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
        "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe')"
        ".Show([Windows.UI.Notifications.ToastNotification]::new($x))"
    )
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                       env=dict(os.environ, VIGIA_TITULO=titulo, VIGIA_TEXTO=texto),
                       timeout=30, capture_output=True, check=False)
    except Exception as exc:  # un aviso que falla no puede tirar el vigia
        log.warning("No salio la notificacion de Windows: %s", exc)

    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": f"{titulo}\n{texto}"}, timeout=20).raise_for_status()
        except Exception as exc:
            log.warning("No salio el Telegram: %s", exc)


# --- Estado y diario ----------------------------------------------------------------
def leer_estado(hoy: str) -> dict | None:
    try:
        e = json.loads(ESTADO.read_text(encoding="utf-8"))
        return e if e.get("fecha") == hoy else None
    except (OSError, ValueError):
        return None


def guardar_estado(estado: dict) -> None:
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")


def anotar(fila: dict) -> None:
    DIARIO_DIR.mkdir(parents=True, exist_ok=True)
    archivo = DIARIO_DIR / f"{fila['fecha'][:7]}.csv"
    nuevo = not archivo.exists()
    with archivo.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fila))
        if nuevo:
            w.writeheader()
        w.writerow(fila)


# --- Chart ----------------------------------------------------------------------------
def estudio_corriendo() -> bool:
    if not LOCK_ESTUDIO.exists():
        return False
    edad = (time.time() - LOCK_ESTUDIO.stat().st_mtime) / 60
    if edad > LOCK_VIEJO_MIN:
        log.warning("Lock del estudio de hace %.0f min: lo ignoro (corrida muerta).", edad)
        return False
    return True


def poner_chart_en_15m(lectura: dict) -> bool:
    """Si el estudio dejo el chart en otro simbolo o timeframe, lo vuelve a GGAL 15m."""
    if "GGAL" in (lectura.get("simbolo") or "") and lectura.get("resolucion") == "15":
        return True
    log.info("Chart en %s %s: lo vuelvo a GGAL 15m.", lectura.get("simbolo"), lectura.get("resolucion"))
    # Timeframe antes que simbolo: al reves el feed se queda pegado (receta del estudio, §1).
    evaluar("TradingViewApi.activeChart().setResolution('15')")
    time.sleep(3)
    evaluar("TradingViewApi.activeChart().setSymbol('BATS:GGAL')")
    time.sleep(8)
    return False


# --- Postura --------------------------------------------------------------------------
def _num(x) -> str:
    return f"{x:.2f}" if isinstance(x, (int, float)) else "?"


def _hora(ms) -> str:
    return datetime.fromtimestamp(ms / 1000, NY).strftime("%H:%M") if ms else "?"


def _minutos_desde(ms, ahora: datetime) -> float:
    return (ahora - datetime.fromtimestamp(ms / 1000, NY)).total_seconds() / 60


def describir(lec: dict) -> tuple[str, str]:
    """Titulo y texto de la postura vigente."""
    if not lec.get("postura"):
        return "GGAL AFUERA", "Sin posicion."
    lado = "LONG" if lec["postura"] > 0 else "SHORT"
    tam = "GRANDE" if lec.get("grande") == 1 else "CHICA"
    rr = f"R:R 1:{lec['rr']:.1f} · " if isinstance(lec.get("rr"), (int, float)) else ""
    return (f"GGAL {lado} {tam} @ {_num(lec.get('precio'))} ({_hora(lec.get('hora'))} NY)",
            f"{rr}SL {_num(lec.get('sl'))} · TP {_num(lec.get('tp'))}")


def una_lectura(estado: dict, ahora: datetime, ultimo_reload: list, arranque: bool = False) -> None:
    lec = json.loads(evaluar(JS_LECTURA))
    if not poner_chart_en_15m(lec):
        return
    if not lec.get("estrategia"):
        if not estado.get("avisado_sin_estrategia"):
            notificar("GGAL Señales: falta la estrategia", "El chart no tiene 'GGAL Señales'. Agregala desde el Pine Editor.")
            estado["avisado_sin_estrategia"] = True
        return

    # Datos viejos: con la rueda abierta tiene que haber una vela de los ultimos minutos.
    if lec.get("ultimaVela") and not arranque:
        atraso = _minutos_desde(lec["ultimaVela"], ahora)
        if atraso > DATOS_VIEJOS_MIN and time.time() - ultimo_reload[0] > 15 * 60:
            log.warning("La ultima vela es de hace %.0f min: recargo la pagina.", atraso)
            evaluar("location.reload()")
            ultimo_reload[0] = time.time()
            return

    postura = int(lec.get("postura") or 0)
    hora = lec.get("hora")
    clave = f"{postura}:{hora}" if postura else "0"
    previa = estado.get("clave")
    estado["clave"] = clave

    if arranque or previa is None:
        # Al arrancar se avisa la postura vigente una vez, sin anotarla como evento.
        titulo, texto = describir(lec)
        notificar(f"Postura actual · {titulo}", texto)
        return
    if clave == previa:
        return

    # Cambio de postura. Si se cerro una posicion, primero la salida.
    if previa != "0":
        cerradas = lec.get("cerradas") or []
        o = cerradas[-1] if cerradas else None
        if o and _minutos_desde(o["tSalida"], ahora) <= RECIENTE_MIN:
            # Resultado sobre el capital inicial (100k), que es contra lo que se mide
            # el riesgo de 0,5% / 1% por operacion.
            pct = o["pnl"] / 100000 * 100
            if o["motivo"].endswith("salida"):  # orden de stop/objetivo de strategy.exit
                motivo = "objetivo" if o["pnl"] > 0 else "stop"
            else:
                motivo = o["motivo"].lower()
            notificar(f"GGAL AFUERA · cierra el {o['lado']} @ {o['salida']:.2f}",
                      f"{motivo} · {o['pnl']:+.0f} USD ({pct:+.2f}% del capital)")
            anotar({"fecha": ahora.strftime("%Y-%m-%d"), "hora_ny": _hora(o["tSalida"]), "evento": "salida",
                    "lado": o["lado"], "tamano": o["tam"], "precio": f"{o['salida']:.2f}",
                    "sl": "", "tp": "", "rr": "", "motivo_salida": motivo, "pnl_pct": f"{pct:.2f}"})

    # Despues, si hay posicion nueva, la entrada (solo si es reciente).
    if postura and hora and _minutos_desde(hora, ahora) <= RECIENTE_MIN:
        titulo, texto = describir(lec)
        notificar(titulo, texto)
        anotar({"fecha": ahora.strftime("%Y-%m-%d"), "hora_ny": _hora(hora), "evento": "entrada",
                "lado": "LONG" if postura > 0 else "SHORT", "tamano": "GRANDE" if lec.get("grande") == 1 else "CHICA",
                "precio": _num(lec.get("precio")), "sl": _num(lec.get("sl")), "tp": _num(lec.get("tp")),
                "rr": f"{lec['rr']:.1f}" if isinstance(lec.get("rr"), (int, float)) else "",
                "motivo_salida": "", "pnl_pct": ""})
    elif postura:
        log.info("Cambio de postura viejo (%s): no se avisa.", clave)


# --- Loop -----------------------------------------------------------------------------
def mantener_despierta(si: bool) -> None:
    # Sin esto el Idle Timeout duerme la maquina a mitad de la rueda. La pantalla
    # puede apagarse: el chart sigue recibiendo datos aunque no pinte.
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if si else 0))


def commitear_diario(hoy: str) -> None:
    archivo = DIARIO_DIR / f"{hoy[:7]}.csv"
    if not archivo.exists():
        return
    rel = archivo.relative_to(REPO).as_posix()
    if not subprocess.run(["git", "status", "--porcelain", rel], cwd=REPO, capture_output=True, text=True).stdout.strip():
        return
    for cmd in (["git", "add", rel],
                ["git", "commit", "-m", f"señales GGAL {hoy}"],
                ["git", "push", "origin", "master"]):
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            log.error("Fallo %s: %s", " ".join(cmd[:2]), (r.stderr or r.stdout).strip())
            return
    log.info("Diario de señales commiteado y pusheado.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--una-vez", action="store_true", help="una sola lectura y sale")
    args = ap.parse_args()

    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-5s | %(message)s",
                        handlers=[logging.FileHandler(LOG_DIR / "ggal_senales_vigia.log", encoding="utf-8"),
                                  logging.StreamHandler(sys.stdout)])
    cargar_env()

    ahora = datetime.now(NY)
    hoy = ahora.strftime("%Y-%m-%d")
    estado = leer_estado(hoy) or {"fecha": hoy}
    ultimo_reload = [0.0]

    if args.una_vez:
        una_lectura(estado, ahora, ultimo_reload, arranque=True)
        guardar_estado(estado)
        return 0

    if ahora.weekday() >= 5:
        log.info("Fin de semana: nada que mirar.")
        return 0
    inicio = ahora.replace(hour=DESDE[0], minute=DESDE[1], second=0, microsecond=0)
    fin = ahora.replace(hour=HASTA[0], minute=HASTA[1], second=0, microsecond=0)
    if ahora >= fin:
        log.info("La rueda de hoy ya termino.")
        return 0

    log.info("=== Vigia GGAL %s: mira de %02d:%02d a %02d:%02d NY ===", hoy, *DESDE, *HASTA)
    mantener_despierta(True)
    avisado_arranque = False
    try:
        while datetime.now(NY) < inicio:
            time.sleep(30)
        while (ahora := datetime.now(NY)) < fin:
            if estudio_corriendo():
                log.info("El estudio diario esta usando el chart; espero.")
            else:
                try:
                    una_lectura(estado, ahora, ultimo_reload, arranque=not avisado_arranque)
                    avisado_arranque = True
                    guardar_estado(estado)
                except Exception as exc:
                    # CDP caido, pagina recargando, etc.: se reintenta en la vuelta siguiente.
                    log.warning("Lectura fallida: %s", exc)
            time.sleep(CADA_SEG)
    finally:
        mantener_despierta(False)
    commitear_diario(hoy)
    log.info("=== Fin del vigia GGAL %s ===", hoy)
    return 0


if __name__ == "__main__":
    sys.exit(main())
