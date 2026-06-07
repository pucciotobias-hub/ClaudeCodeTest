# =============================================================================
# Monitor de Divergencia GGAL vs RFX20 v2.0
# Arbitraje estadístico con z-score dinámico — Matba Rofex / pyRofex
# =============================================================================

import os
import math
import time
import logging
import threading
from collections import deque
from datetime import datetime
from statistics import mean, stdev

import pyRofex
from pyRofex import MarketDataEntry

# --- CONFIGURACIÓN -----------------------------------------------------------

USUARIO  = os.environ.get("ROFEX_USER",     "pucciotobias23427")
PASSWORD = os.environ.get("ROFEX_PASSWORD", "mndnoL2$")
CUENTA   = os.environ.get("ROFEX_ACCOUNT",  "REM23427")

TICKERS = ["GGAL/JUN26", "RFX20/JUN26"]

ZSCORE_UMBRAL     = 2.0   # σ para disparar alerta
VENTANA_SPREAD    = 100   # muestras para calcular μ y σ del spread
MIN_MUESTRAS      = 10    # muestras mínimas antes de alertar
COOLDOWN_ALERTA   = 60    # segundos mínimos entre alertas consecutivas
TIMEOUT_DATOS     = 30    # segundos sin datos antes de advertir
RECONEXION_MAX    = 5     # intentos máximos de reconexión
INTERVALO_DISPLAY = 2     # segundos entre refreshes del display

# --- LOGGING (solo a archivo, el display de consola es manual) ---------------

_file_handler = logging.FileHandler("monitor_divergencia.log", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

log = logging.getLogger("monitor")
log.setLevel(logging.INFO)
log.addHandler(_file_handler)

# --- ESTADO GLOBAL -----------------------------------------------------------

precios        = {t: None for t in TICKERS}
ultimo_update  = {t: 0.0  for t in TICKERS}
spread_history = deque(maxlen=VENTANA_SPREAD)

ultima_alerta_ts  = 0.0
ultimo_mensaje_ts = time.time()

_print_lock = threading.Lock()

# --- MID-PRICE ---------------------------------------------------------------

def calcular_mid(market_data):
    """Retorna (best bid + best ask) / 2. Fallback a last trade si no hay book."""
    bids   = market_data.get("BI")
    offers = market_data.get("OF")

    bid = bids[0].get("price")   if bids   else None
    ask = offers[0].get("price") if offers else None

    if bid and ask and bid > 0 and ask > 0:
        return (bid + ask) / 2

    last = market_data.get("LA")
    if last:
        p = last.get("price")
        if p and p > 0:
            return p

    return None

# --- SPREAD Y Z-SCORE --------------------------------------------------------

def calcular_spread_zscore():
    """
    Spread = ln(GGAL / RFX20). Normalizar con log elimina diferencias de escala
    y hace el spread estacionario (apropiado para arbitraje estadístico).
    Retorna (spread_actual, media, z_score) — alguno puede ser None si hay
    datos insuficientes.
    """
    p_ggal  = precios["GGAL/JUN26"]
    p_rfx20 = precios["RFX20/JUN26"]

    if not p_ggal or not p_rfx20 or p_rfx20 <= 0:
        return None, None, None

    s = math.log(p_ggal / p_rfx20)
    spread_history.append(s)

    n = len(spread_history)
    if n < MIN_MUESTRAS:
        return s, None, None

    mu    = mean(spread_history)
    sigma = stdev(spread_history)

    if sigma == 0:
        return s, mu, None

    return s, mu, (s - mu) / sigma

# --- VERIFICACIÓN Y ALERTA ---------------------------------------------------

def verificar_divergencia():
    global ultima_alerta_ts

    s, mu, z = calcular_spread_zscore()

    if z is None:
        return

    ahora = time.time()
    if abs(z) < ZSCORE_UMBRAL or (ahora - ultima_alerta_ts) < COOLDOWN_ALERTA:
        return

    ultima_alerta_ts = ahora

    p_ggal  = precios["GGAL/JUN26"]
    p_rfx20 = precios["RFX20/JUN26"]
    direccion = "GGAL sobrevaluada vs RFX20" if z > 0 else "GGAL subvaluada vs RFX20"

    msg = (
        f"ALERTA DIVERGENCIA | Z: {z:+.2f}s | "
        f"GGAL: {p_ggal:.2f} | RFX20: {p_rfx20:.2f} | "
        f"Spread: {s:.4f} (mu={mu:.4f}) | {direccion}"
    )

    log.warning(msg)

    with _print_lock:
        hora = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{hora}] *** {msg} ***", flush=True)

# --- HANDLERS DEL WEBSOCKET --------------------------------------------------

def market_data_handler(message):
    global ultimo_mensaje_ts

    try:
        ticker = message["instrumentId"]["symbol"]
        if ticker not in precios:
            return

        mid = calcular_mid(message.get("marketData", {}))
        if mid is None:
            return

        precios[ticker]       = mid
        ultimo_update[ticker] = time.time()
        ultimo_mensaje_ts     = time.time()

        if all(v is not None for v in precios.values()):
            verificar_divergencia()

    except Exception as e:
        log.error(f"Error procesando mensaje: {e} | {message}")


def error_handler(message):
    log.error(f"WS error: {message}")


def exception_handler(e):
    log.error(f"WS excepción: {e}")

# --- DISPLAY EN TIEMPO REAL --------------------------------------------------

def mostrar_estado():
    p_ggal  = precios["GGAL/JUN26"]
    p_rfx20 = precios["RFX20/JUN26"]
    n = len(spread_history)

    if p_ggal is None or p_rfx20 is None:
        linea = "Esperando precios..."
    else:
        s = math.log(p_ggal / p_rfx20)

        if n >= MIN_MUESTRAS:
            mu    = mean(spread_history)
            sigma = stdev(spread_history)
            z     = (s - mu) / sigma if sigma else 0.0
            z_str = f"{z:+.2f}s"
        else:
            z_str = f"acumulando {n}/{MIN_MUESTRAS}"

        cooldown = max(0.0, COOLDOWN_ALERTA - (time.time() - ultima_alerta_ts))
        cd_str   = f" | CD: {cooldown:.0f}s" if cooldown > 0 else ""

        linea = (
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"GGAL: {p_ggal:.2f} | RFX20: {p_rfx20:.2f} | "
            f"Spread: {s:.4f} | Z: {z_str} | N: {n}{cd_str}"
        )

    with _print_lock:
        print(f"\r{linea:<115}", end="", flush=True)


def verificar_heartbeat():
    sin_datos = time.time() - ultimo_mensaje_ts
    if sin_datos > TIMEOUT_DATOS:
        log.warning(f"Sin datos del feed hace {sin_datos:.0f}s")
        with _print_lock:
            print(f"\n[WARN] Sin datos del feed hace {sin_datos:.0f}s — posible desconexión", flush=True)

# --- CONEXIÓN CON RECONEXIÓN AUTOMÁTICA --------------------------------------

def conectar():
    log.info("Conectando a Matba Rofex (ReMarkets)...")

    pyRofex.initialize(
        user=USUARIO,
        password=PASSWORD,
        account=CUENTA,
        environment=pyRofex.Environment.REMARKET
    )

    pyRofex.init_websocket_connection(
        market_data_handler=market_data_handler,
        error_handler=error_handler,
        exception_handler=exception_handler
    )

    pyRofex.market_data_subscription(
        tickers=TICKERS,
        entries=[MarketDataEntry.LAST, MarketDataEntry.BIDS, MarketDataEntry.OFFERS]
    )

    log.info(
        f"Suscripcion activa | Umbral: {ZSCORE_UMBRAL}s | "
        f"Ventana: {VENTANA_SPREAD} muestras | Cooldown: {COOLDOWN_ALERTA}s"
    )
    print(
        f"\nMonitor activo - Umbral: {ZSCORE_UMBRAL}s | "
        f"Ventana: {VENTANA_SPREAD} muestras | Cooldown: {COOLDOWN_ALERTA}s\n"
        f"Alertas guardadas en: monitor_divergencia.log\n"
        f"Ctrl+C para detener.\n"
    )

# --- PUNTO DE ENTRADA --------------------------------------------------------

if __name__ == "__main__":
    intentos = 0

    while True:
        try:
            conectar()
            intentos = 0

            while True:
                time.sleep(INTERVALO_DISPLAY)
                mostrar_estado()
                verificar_heartbeat()

        except KeyboardInterrupt:
            print("\nMonitor detenido.")
            log.info("Monitor detenido por el usuario.")
            break

        except Exception as e:
            intentos += 1
            if intentos > RECONEXION_MAX:
                log.critical("Máximo de reconexiones alcanzado. Abortando.")
                print("\nMáximo de reconexiones alcanzado. Abortando.")
                break

            espera = min(2 ** intentos, 60)  # backoff exponencial, tope 60s
            log.error(f"Error (intento {intentos}/{RECONEXION_MAX}): {e}. Reintentando en {espera}s...")
            print(f"\n[ERROR] Reconectando en {espera}s... (intento {intentos}/{RECONEXION_MAX})")
            time.sleep(espera)
