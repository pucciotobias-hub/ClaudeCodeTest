# =============================================================================
# Módulo 2 — Motor Técnico MTF (Multi-TimeFrame)
# Tendencia simultánea en 5m / 15m / Diario, VWAP intradiario y distancia a S/R
# =============================================================================
#
# NOTA SOBRE LA FUENTE DE DATOS:
# Se usa yfinance (datos reales, aunque con delay) en lugar de pyRofex en vivo.
# Streamlit re-ejecuta todo el script en cada interacción del usuario, por lo
# que mantener una conexión websocket persistente requeriría threads de fondo
# + st.session_state/st.cache_resource — complejidad innecesaria para este
# esqueleto. Cuando se quiera pasar a datos de book en tiempo real, se puede
# reusar el patrón de conexión de monitor.py (pyRofex.initialize +
# init_websocket_connection + market_data_subscription con handlers de
# market_data/error/exception) corriendo en un thread de fondo que escriba
# en st.session_state.
#
# =============================================================================

import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURACIÓN -----------------------------------------------------------

# Timeframes a evaluar: (intervalo yfinance, período de descarga, etiqueta)
TIMEFRAMES = [
    ("5m",  "5d",  "5 minutos"),
    ("15m", "1mo", "15 minutos"),
    ("1d",  "6mo", "Diario"),
]

VENTANA_SR = 20            # velas para detectar soporte/resistencia (mín/máx móvil)
CACHE_TTL_TECNICO = 120    # segundos — refrescar datos técnicos cada 2 minutos

# Mapeo de tickers de pyRofex (futuros locales) a sus equivalentes/proxies en
# Yahoo Finance, ya que yfinance no tiene los contratos de Matba Rofex.
TICKER_YFINANCE = {
    "GGAL/JUN26":  "GGAL",   # ADR de Grupo Financiero Galicia
    "RFX20/JUN26": "^MERV",  # Proxy del índice Merval para RFX20
    "BMA":         "BMA",
}

# --- OBTENCIÓN DE DATOS -------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL_TECNICO)
def obtener_datos_mtf(ticker: str) -> dict:
    """
    Descarga velas para cada timeframe configurado (5m, 15m, Diario) del
    ticker pedido. Retorna {etiqueta_timeframe: DataFrame OHLCV}.
    Los DataFrames vacíos indican que no hubo datos disponibles para ese TF.
    """
    simbolo_yf = TICKER_YFINANCE.get(ticker, ticker)
    datos = {}

    for intervalo, periodo, etiqueta in TIMEFRAMES:
        try:
            df = yf.Ticker(simbolo_yf).history(period=periodo, interval=intervalo)
            datos[etiqueta] = df
        except Exception:
            datos[etiqueta] = pd.DataFrame()

    return datos

# --- TENDENCIA MULTI-TIMEFRAME -------------------------------------------------

def calcular_tendencia(df: pd.DataFrame) -> str:
    """
    Determina la tendencia de una serie de velas comparando el precio de
    cierre actual contra la SMA20: por encima → "alcista", por debajo →
    "bajista", y dentro de una banda de ±0.15% → "lateral".
    Devuelve "sin datos" si no hay suficientes velas para calcular la SMA.
    """
    if df is None or df.empty or len(df) < 20:
        return "sin datos"

    cierre_actual = df["Close"].iloc[-1]
    sma20 = df["Close"].rolling(window=20).mean().iloc[-1]

    diferencia_pct = (cierre_actual - sma20) / sma20 * 100

    if diferencia_pct > 0.15:
        return "alcista"
    if diferencia_pct < -0.15:
        return "bajista"
    return "lateral"


def construir_tabla_tendencia_mtf(datos_mtf: dict) -> pd.DataFrame:
    """
    Arma una tabla resumen con la tendencia detectada en cada timeframe,
    lista para mostrar con st.dataframe/st.table.
    """
    filas = []
    for etiqueta, df in datos_mtf.items():
        precio_actual = round(float(df["Close"].iloc[-1]), 2) if not df.empty else None
        filas.append({
            "Timeframe": etiqueta,
            "Tendencia": calcular_tendencia(df),
            "Último precio": precio_actual,
        })

    return pd.DataFrame(filas)

# --- VWAP INTRADIARIO ----------------------------------------------------------

def calcular_vwap(df_intradia: pd.DataFrame) -> pd.Series:
    """
    Calcula el VWAP (Volume Weighted Average Price) acumulado intradiario:

        precio_típico = (High + Low + Close) / 3
        VWAP = Σ(precio_típico · volumen) / Σ(volumen)

    El acumulado se reinicia cada día de calendario (comportamiento estándar
    del VWAP intradiario). Devuelve una Serie alineada al índice del DataFrame.
    """
    if df_intradia is None or df_intradia.empty:
        return pd.Series(dtype="float64")

    precio_tipico = (df_intradia["High"] + df_intradia["Low"] + df_intradia["Close"]) / 3
    volumen = df_intradia["Volume"]

    dia = df_intradia.index.normalize()
    pv_acumulado = (precio_tipico * volumen).groupby(dia).cumsum()
    vol_acumulado = volumen.groupby(dia).cumsum()

    return pv_acumulado / vol_acumulado.replace(0, pd.NA)

# --- SOPORTE / RESISTENCIA ------------------------------------------------------

def detectar_soporte_resistencia(df: pd.DataFrame, ventana: int = VENTANA_SR) -> tuple:
    """
    Detección simple de soporte/resistencia: mínimo y máximo móvil de las
    últimas `ventana` velas. Es un enfoque básico apto para un esqueleto;
    una mejora futura sería identificar pivots (máximos/mínimos locales) o
    zonas de acumulación de volumen.
    Retorna (soporte, resistencia), o (None, None) si no hay datos suficientes.
    """
    if df is None or df.empty or len(df) < ventana:
        return None, None

    soporte = float(df["Low"].rolling(window=ventana).min().iloc[-1])
    resistencia = float(df["High"].rolling(window=ventana).max().iloc[-1])

    return round(soporte, 2), round(resistencia, 2)


def calcular_distancia_sr(precio_actual: float, soporte: float, resistencia: float) -> dict:
    """
    Calcula la distancia porcentual del precio actual al soporte y a la
    resistencia más cercanos. Retorna un diccionario con ambas distancias
    en % (positivas = el nivel está por encima del precio actual).
    """
    if precio_actual is None or soporte is None or resistencia is None:
        return {"dist_soporte_pct": None, "dist_resistencia_pct": None}

    return {
        "dist_soporte_pct": round((precio_actual - soporte) / precio_actual * 100, 2),
        "dist_resistencia_pct": round((resistencia - precio_actual) / precio_actual * 100, 2),
    }
