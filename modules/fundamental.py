# =============================================================================
# Módulo 3 — Análisis Fundamental y Contable
# Ratios de liquidez, apalancamiento (Debt/Equity) y P/E de bancos argentinos
# =============================================================================

import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURACIÓN -----------------------------------------------------------

TICKERS_BANCOS = ["GGAL", "BMA"]

CACHE_TTL_FUNDAMENTAL = 3600  # segundos — los balances no cambian intradía

# --- OBTENCIÓN DE DATOS -------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL_FUNDAMENTAL)
def obtener_metricas_fundamentales(tickers: list = None) -> pd.DataFrame:
    """
    Extrae del último balance/perfil disponible en Yahoo Finance las métricas
    clave de cada banco: ratios de liquidez (current/quick ratio), nivel de
    apalancamiento (debt/equity) y P/E (trailing).

    NOTA: los ADRs bancarios suelen tener campos incompletos o nulos en
    `Ticker.info` (Yahoo no siempre consolida el balance local). Se manejan
    los `None` explícitamente para que la tabla se muestre sin romper aunque
    falten datos — es el comportamiento esperado, no un error.
    """
    tickers = tickers or TICKERS_BANCOS
    filas = []

    for simbolo in tickers:
        try:
            info = yf.Ticker(simbolo).info
        except Exception:
            info = {}

        filas.append({
            "Ticker": simbolo,
            "Current Ratio (liquidez)": info.get("currentRatio"),
            "Quick Ratio (liquidez)": info.get("quickRatio"),
            "Debt/Equity (apalancamiento)": info.get("debtToEquity"),
            "P/E (trailing)": info.get("trailingPE"),
        })

    return pd.DataFrame(filas).set_index("Ticker")
