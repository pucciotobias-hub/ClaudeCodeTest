# =============================================================================
# Módulo 1 — Contexto Macro (yfinance)
# "Termómetro Global": estado del contexto macro para un trade long en Argentina
# =============================================================================

import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURACIÓN -----------------------------------------------------------

# Tickers monitoreados y su etiqueta para mostrar en el dashboard
TICKERS_MACRO = {
    "SPY":  "S&P 500 (SPY)",
    "DX-Y.NYB": "Índice Dólar (DXY)",
    "^VIX": "Volatilidad (VIX)",
    "EWZ":  "Brasil (EWZ)",
    "ARGT": "Argentina (ARGT)",
}

CACHE_TTL_MACRO = 300  # segundos — refrescar contexto macro cada 5 minutos

# --- OBTENCIÓN DE DATOS -------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL_MACRO)
def obtener_contexto_macro() -> pd.DataFrame:
    """
    Descarga el último precio y la variación % vs el cierre previo para
    cada ticker del termómetro global. Retorna un DataFrame indexado por
    símbolo con columnas: nombre, precio, variacion_pct.
    """
    filas = []

    for simbolo, nombre in TICKERS_MACRO.items():
        try:
            hist = yf.Ticker(simbolo).history(period="5d")
            if len(hist) < 2:
                filas.append({"simbolo": simbolo, "nombre": nombre, "precio": None, "variacion_pct": None})
                continue

            precio_actual = hist["Close"].iloc[-1]
            precio_previo = hist["Close"].iloc[-2]
            variacion_pct = (precio_actual - precio_previo) / precio_previo * 100

            filas.append({
                "simbolo": simbolo,
                "nombre": nombre,
                "precio": round(float(precio_actual), 2),
                "variacion_pct": round(float(variacion_pct), 2),
            })
        except Exception:
            filas.append({"simbolo": simbolo, "nombre": nombre, "precio": None, "variacion_pct": None})

    return pd.DataFrame(filas).set_index("simbolo")

# --- SEMÁFOROS ----------------------------------------------------------------

def _semaforo_por_variacion(variacion_pct, umbral_verde, umbral_rojo, invertido=False):
    """
    Clasifica una variación % en verde/amarillo/rojo según umbrales.
    Si `invertido` es True, una variación negativa es la favorable
    (ej. DXY: dólar débil ayuda a emergentes).
    """
    if variacion_pct is None:
        return "amarillo"

    v = -variacion_pct if invertido else variacion_pct

    if v > umbral_verde:
        return "verde"
    if v < umbral_rojo:
        return "rojo"
    return "amarillo"


def evaluar_semaforo(metricas: pd.DataFrame) -> dict:
    """
    Evalúa cada componente del termómetro global y devuelve un diccionario
    {simbolo: "verde" | "amarillo" | "rojo"} con sesgo "long Argentina":

      - SPY:  suba ayuda al apetito de riesgo en emergentes (risk-on)
      - VIX:  volatilidad baja = apetito de riesgo (umbral por nivel, no variación)
      - DXY:  dólar débil ayuda a emergentes (se invierte la lectura)
      - EWZ/ARGT: proxy directo de apetito regional/local
    """
    estados = {}

    for simbolo in TICKERS_MACRO:
        if simbolo not in metricas.index:
            estados[simbolo] = "amarillo"
            continue

        fila = metricas.loc[simbolo]
        variacion = fila["variacion_pct"]
        precio = fila["precio"]

        if simbolo == "SPY":
            estados[simbolo] = _semaforo_por_variacion(variacion, umbral_verde=0.3, umbral_rojo=-0.3)

        elif simbolo == "^VIX":
            # El VIX se evalúa por nivel absoluto, no por variación
            if precio is None:
                estados[simbolo] = "amarillo"
            elif precio < 18:
                estados[simbolo] = "verde"
            elif precio > 25:
                estados[simbolo] = "rojo"
            else:
                estados[simbolo] = "amarillo"

        elif simbolo == "DX-Y.NYB":
            estados[simbolo] = _semaforo_por_variacion(variacion, umbral_verde=0.2, umbral_rojo=-0.2, invertido=True)

        else:  # EWZ, ARGT
            estados[simbolo] = _semaforo_por_variacion(variacion, umbral_verde=0.5, umbral_rojo=-0.5)

    return estados


def semaforo_global(estados: dict) -> str:
    """
    Resume los semáforos individuales en un veredicto global por voto
    mayoritario simple ("verde" | "amarillo" | "rojo").
    """
    conteo = {"verde": 0, "amarillo": 0, "rojo": 0}
    for estado in estados.values():
        conteo[estado] += 1

    return max(conteo, key=conteo.get)
