# =============================================================================
# Monitor de Divergencia GGAL vs RFX20 — v3.0
# Arbitraje estadistico (solo SEÑALES, NO ejecuta ordenes) — Matba Rofex / pyRofex
#
# Detecta desvios estadisticos del spread log(GGAL/RFX20) via z-score sobre una
# ventana movil y emite una SEÑAL cuando |z| supera el umbral. El sistema NO
# envia ni cancela ordenes: unicamente observa market data y avisa.
# =============================================================================

import os
import sys
import math
import time
import logging
from collections import deque
from datetime import datetime
from statistics import mean, stdev

import pyRofex
from pyRofex import MarketDataEntry


# --- CARGA DE CREDENCIALES (.env o variables de entorno) ---------------------

def cargar_dotenv(nombre=".env"):
    """
    Carga un archivo .env (KEY=VALUE por linea) ubicado junto a este script,
    sin dependencias externas. Las variables de entorno reales tienen prioridad.
    """
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre)
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


cargar_dotenv()

# Credenciales: SIEMPRE desde el entorno. Nunca hardcodear en el codigo.
USUARIO  = os.environ.get("ROFEX_USER")
PASSWORD = os.environ.get("ROFEX_PASSWORD")
CUENTA   = os.environ.get("ROFEX_ACCOUNT")

# Entorno: REMARKET (pruebas/homologacion) por defecto. LIVE solo cuando el
# broker habilite las credenciales productivas (ROFEX_ENV=LIVE).
ENV_NAME    = os.environ.get("ROFEX_ENV", "REMARKET").upper()
ENVIRONMENT = pyRofex.Environment.LIVE if ENV_NAME == "LIVE" else pyRofex.Environment.REMARKET

# --- CONFIGURACION -----------------------------------------------------------

TICKERS = ["GGAL/JUN26", "RFX20/JUN26"]

ZSCORE_UMBRAL     = 2.0   # desvios estandar para disparar la señal
VENTANA_SPREAD    = 100   # muestras para calcular media y desvio del spread
MIN_MUESTRAS      = 10    # muestras minimas antes de poder emitir señal
COOLDOWN_ALERTA   = 60    # segundos minimos entre señales consecutivas
TIMEOUT_DATOS     = 30    # segundos sin datos -> se fuerza reconexion
RECONEXION_MAX    = 5     # intentos maximos de reconexion antes de abortar
INTERVALO         = 1.0   # segundos entre muestreos del spread (cadencia fija)

# --- LOGGING (a archivo; el display de consola es manual) --------------------

_file_handler = logging.FileHandler("monitor_divergencia.log", encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

log = logging.getLogger("monitor")
log.setLevel(logging.INFO)
log.addHandler(_file_handler)

# --- ESTADO GLOBAL -----------------------------------------------------------
# El handler del WebSocket (hilo de fondo) SOLO escribe escalares en estos dicts.
# Todo el calculo del spread/z-score vive en el hilo principal (procesar_tick),
# por lo que no hay estructuras compartidas mutadas desde dos hilos a la vez.

precios        = {t: None for t in TICKERS}
ultimo_update  = {t: 0.0  for t in TICKERS}
spread_history = deque(maxlen=VENTANA_SPREAD)

ultima_alerta_ts  = 0.0
ultimo_mensaje_ts = time.time()

# --- MID-PRICE ---------------------------------------------------------------

def calcular_mid(market_data):
    """Retorna (best bid + best ask) / 2. Fallback al ultimo operado si no hay book."""
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

# --- DISPLAY -----------------------------------------------------------------

def _render(texto):
    """Reescribe la linea de estado en consola (ASCII puro para evitar problemas
    de encoding en la consola de Windows)."""
    linea = f"[{datetime.now():%H:%M:%S}] {texto}"
    print(f"\r{linea:<120}", end="", flush=True)

# --- MUESTREO + EVALUACION (hilo principal, cadencia fija) --------------------

def procesar_tick():
    """
    Toma los mids vigentes, calcula el spread log(GGAL/RFX20), lo agrega al
    historial, calcula el z-score sobre la ventana movil y emite una SEÑAL si
    |z| >= umbral (respetando el cooldown). Tambien refresca el display.

    Se invoca a intervalo fijo (INTERVALO) desde el loop principal, de modo que
    el muestreo del spread es regular en el tiempo y no depende del ritmo de
    llegada de mensajes del feed.
    """
    global ultima_alerta_ts

    p_ggal  = precios["GGAL/JUN26"]
    p_rfx20 = precios["RFX20/JUN26"]

    if not p_ggal or not p_rfx20 or p_rfx20 <= 0:
        _render("Esperando precios de ambos instrumentos...")
        return

    s = math.log(p_ggal / p_rfx20)
    spread_history.append(s)
    n = len(spread_history)

    if n < MIN_MUESTRAS:
        _render(f"GGAL: {p_ggal:.2f} | RFX20: {p_rfx20:.2f} | "
                f"Spread: {s:.5f} | acumulando {n}/{MIN_MUESTRAS}")
        return

    mu    = mean(spread_history)
    sigma = stdev(spread_history)
    z     = (s - mu) / sigma if sigma else 0.0

    ahora    = time.time()
    cooldown = max(0.0, COOLDOWN_ALERTA - (ahora - ultima_alerta_ts))

    if abs(z) >= ZSCORE_UMBRAL and cooldown == 0:
        ultima_alerta_ts = ahora
        cooldown         = COOLDOWN_ALERTA
        direccion = "GGAL sobrevaluada vs RFX20" if z > 0 else "GGAL subvaluada vs RFX20"
        msg = (
            f"SEÑAL DE DIVERGENCIA | z={z:+.2f} (umbral {ZSCORE_UMBRAL}) | "
            f"GGAL: {p_ggal:.2f} | RFX20: {p_rfx20:.2f} | "
            f"Spread: {s:.5f} (mu={mu:.5f}, sigma={sigma:.5f}) | {direccion}"
        )
        log.warning(msg)
        print(f"\n[{datetime.now():%H:%M:%S}] *** {msg} ***", flush=True)

    cd_str = f" | CD: {cooldown:.0f}s" if cooldown > 0 else ""
    _render(f"GGAL: {p_ggal:.2f} | RFX20: {p_rfx20:.2f} | "
            f"Spread: {s:.5f} | z={z:+.2f} | N: {n}{cd_str}")

# --- HANDLERS DEL WEBSOCKET (hilo de fondo) ----------------------------------

def market_data_handler(message):
    """Solo actualiza el mid vigente de cada ticker y marca actividad del feed."""
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

    except Exception as e:
        log.error(f"Error procesando mensaje: {e} | {message}")


def error_handler(message):
    log.error(f"WS error: {message}")


def exception_handler(e):
    log.error(f"WS excepcion: {e}")

# --- CONEXION ----------------------------------------------------------------

def validar_simbolos():
    """Best-effort: avisa si los tickers configurados no figuran en el listado
    del mercado (contrato vencido o formato erroneo). Nunca aborta el arranque."""
    try:
        data     = pyRofex.get_all_instruments()
        simbolos = {i["instrumentId"]["symbol"] for i in data.get("instruments", [])}
        faltantes = [t for t in TICKERS if t not in simbolos]
        if faltantes:
            log.warning(f"Simbolos no encontrados en el mercado: {faltantes}. "
                        f"Verifica vigencia/formato del contrato.")
            print(f"\n[WARN] Simbolos no encontrados: {faltantes} "
                  f"-> revisa que los contratos esten vigentes.")
    except Exception as e:
        log.info(f"No se pudo validar simbolos (se continua igual): {e}")


def conectar():
    global ultimo_mensaje_ts

    log.info(f"Conectando a Matba Rofex ({ENV_NAME})...")
    pyRofex.initialize(
        user=USUARIO,
        password=PASSWORD,
        account=CUENTA,
        environment=ENVIRONMENT,
    )

    validar_simbolos()

    pyRofex.init_websocket_connection(
        market_data_handler=market_data_handler,
        error_handler=error_handler,
        exception_handler=exception_handler,
    )

    pyRofex.market_data_subscription(
        tickers=TICKERS,
        entries=[MarketDataEntry.LAST, MarketDataEntry.BIDS, MarketDataEntry.OFFERS],
    )

    # Reset del heartbeat: recien (re)conectados, no debe dispararse el timeout.
    ultimo_mensaje_ts = time.time()

    log.info(
        f"Suscripcion activa ({ENV_NAME}) | Umbral: {ZSCORE_UMBRAL} | "
        f"Ventana: {VENTANA_SPREAD} muestras | Cooldown: {COOLDOWN_ALERTA}s"
    )
    print(
        f"\nMonitor activo ({ENV_NAME}) - solo SEÑALES, no opera.\n"
        f"Umbral: z>={ZSCORE_UMBRAL} | Ventana: {VENTANA_SPREAD} muestras "
        f"(@{INTERVALO}s) | Cooldown: {COOLDOWN_ALERTA}s\n"
        f"Señales guardadas en: monitor_divergencia.log\n"
        f"Ctrl+C para detener.\n"
    )


def cerrar_conexion():
    """Cierra el WebSocket previo. Idempotente: ignora errores si ya esta cerrado."""
    try:
        pyRofex.close_websocket_connection()
    except Exception:
        pass

# --- VALIDACION DE ARRANQUE --------------------------------------------------

def validar_credenciales():
    faltan = [nombre for nombre, valor in (
        ("ROFEX_USER", USUARIO),
        ("ROFEX_PASSWORD", PASSWORD),
        ("ROFEX_ACCOUNT", CUENTA),
    ) if not valor]
    if faltan:
        print("ERROR: faltan credenciales: " + ", ".join(faltan))
        print("Definilas como variables de entorno o en un archivo .env "
              "(copia .env.example a .env y completa los valores).")
        sys.exit(1)

# --- PUNTO DE ENTRADA --------------------------------------------------------

if __name__ == "__main__":
    validar_credenciales()

    intentos = 0
    while True:
        try:
            conectar()
            intentos = 0

            # Loop de muestreo: cadencia fija + deteccion de feed caido.
            while True:
                time.sleep(INTERVALO)
                procesar_tick()

                sin_datos = time.time() - ultimo_mensaje_ts
                if sin_datos > TIMEOUT_DATOS:
                    # Feed mudo (desconexion silenciosa): forzamos reconexion.
                    raise ConnectionError(f"Sin datos del feed hace {sin_datos:.0f}s")

        except KeyboardInterrupt:
            print("\nMonitor detenido por el usuario.")
            log.info("Monitor detenido por el usuario.")
            cerrar_conexion()
            break

        except Exception as e:
            cerrar_conexion()
            intentos += 1

            if intentos > RECONEXION_MAX:
                log.critical("Maximo de reconexiones alcanzado. Abortando.")
                print("\nMaximo de reconexiones alcanzado. Abortando.")
                break

            espera = min(2 ** intentos, 60)  # backoff exponencial, tope 60s
            log.error(f"Conexion perdida (intento {intentos}/{RECONEXION_MAX}): {e}. "
                      f"Reintentando en {espera}s...")
            print(f"\n[ERROR] {e} -> reconectando en {espera}s "
                  f"(intento {intentos}/{RECONEXION_MAX})")
            time.sleep(espera)
