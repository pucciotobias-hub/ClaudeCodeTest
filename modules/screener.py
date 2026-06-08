# =============================================================================
# Módulo 4 — Screener Sectorial Inteligente
# Compara acciones de un sector según múltiplos de valuación, rentabilidad y
# solidez financiera, y produce un score 0-100 ponderado según el "ADN" de
# cada sector (ej. semiconductores tolera P/E alto, nuclear exige caja sólida)
# =============================================================================

import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURACIÓN -----------------------------------------------------------

SECTORES: dict = {
    "IA/Semiconductores": ["NVDA", "AMD", "TSM", "ASML", "PLTR"],
    "Nuclear/Uranio": ["CCJ", "UUUU", "NXE", "LEU"],
    "Fintech/Latam": ["MELI", "NU", "PAGS", "STNE"],
}

CACHE_TTL_SCREENER = 3600  # segundos — los múltiplos fundamentales no cambian intradía

# Métricas crudas que entran al motor de scoring, e indicación de si para
# esa métrica "menor es mejor" (True, ej. P/E, PEG, Debt/Equity) o "mayor es
# mejor" (False, ej. márgenes, crecimiento, momentum). Se usa tanto al
# normalizar como al resaltar los mejores/peores ratios en la tabla.
#
# NOTA: "Beta" y "Market Cap (B USD)" se extraen y se muestran en la tabla,
# pero quedan FUERA de este diccionario a propósito — son datos de contexto
# (tamaño, volatilidad relativa) sin una dirección universal de "mejor/peor"
# para un score de calidad fundamental, así que no se normalizan ni resaltan.
METRICAS_MENOR_ES_MEJOR: dict = {
    "P/E Trailing": True,
    "P/E Forward": True,
    "PEG Ratio": True,
    "Price/Sales": True,
    "Margen Bruto": False,
    "Crecimiento Ingresos": False,
    "ROE": False,
    "Debt/Equity": True,
    "Dividend Yield": False,
    "Momentum 3M (%)": False,
}

# Tablas de ponderación por sector (cada una suma 1.0). "_default" se usa
# para cualquier sector sin tabla propia (ej. Fintech/Latam).
PESOS_POR_SECTOR: dict = {
    "IA/Semiconductores": {
        "P/E Trailing": 0.0,           # se tolera P/E alto: sin peso...
        "P/E Forward": 0.0,
        "PEG Ratio": 0.05,             # ...pero el PEG sí entra: valuación vs. crecimiento
        "Price/Sales": 0.05,
        "Margen Bruto": 0.20,          # peso reforzado
        "Crecimiento Ingresos": 0.35,  # peso reforzado — motor de la tesis IA
        "ROE": 0.10,
        "Debt/Equity": 0.05,
        "Dividend Yield": 0.0,         # irrelevante: las growth tech no suelen repartir
        "Momentum 3M (%)": 0.20,       # confirmación técnica en un sector momentum-driven
    },
    "Nuclear/Uranio": {
        "P/E Trailing": 0.05,
        "P/E Forward": 0.05,
        "PEG Ratio": 0.05,
        "Price/Sales": 0.05,
        "Margen Bruto": 0.05,
        "Crecimiento Ingresos": 0.10,
        "ROE": 0.05,
        "Debt/Equity": 0.35,           # foco en solidez del balance
        "Dividend Yield": 0.10,        # sector más maduro: el ingreso importa
        "Momentum 3M (%)": 0.15,
    },
    "_default": {
        "P/E Trailing": 0.10,
        "P/E Forward": 0.10,
        "PEG Ratio": 0.10,
        "Price/Sales": 0.10,
        "Margen Bruto": 0.10,
        "Crecimiento Ingresos": 0.15,
        "ROE": 0.10,
        "Debt/Equity": 0.10,
        "Dividend Yield": 0.05,
        "Momentum 3M (%)": 0.10,
    },
}

PENALIZACION_CAJA_NUCLEAR = 15  # puntos a restar si no genera caja (solo Nuclear/Uranio)

# --- OBTENCIÓN DE DATOS -------------------------------------------------------

def _calcular_momentum_3m(simbolo: str) -> float | None:
    """
    Variación porcentual del precio de cierre entre el primer y el último
    cierre disponible de los últimos 3 meses — usada como sub-score técnico
    de "momentum" dentro del scoring sectorial (confirma o contradice la
    tesis fundamental con la tendencia de precio reciente). Devuelve `None`
    si Yahoo Finance falla o no hay historial suficiente, igual que el resto
    de las métricas de este módulo.
    """
    try:
        historial = yf.Ticker(simbolo).history(period="3mo")
    except Exception:
        return None

    if historial.empty or len(historial) < 2:
        return None

    primero = float(historial["Close"].iloc[0])
    ultimo = float(historial["Close"].iloc[-1])
    if primero == 0:
        return None

    return round((ultimo - primero) / primero * 100, 2)


@st.cache_data(ttl=CACHE_TTL_SCREENER)
def obtener_metricas_sectoriales(tickers: list) -> pd.DataFrame:
    """
    Descarga de Yahoo Finance los múltiplos de valuación, rentabilidad y
    contexto de cada ticker del sector:

      - Valuación: P/E trailing/forward, PEG Ratio (valuación vs.
        crecimiento — clave para no penalizar a una IA cara que crece
        rápido), Price-to-Sales.
      - Rentabilidad y solidez: margen bruto, crecimiento de ingresos, ROE,
        Debt/Equity.
      - Ingreso: Dividend Yield.
      - Técnico: Momentum 3M — variación % de precio en los últimos 3 meses
        (vía `_calcular_momentum_3m`, vuelco directo de `Ticker.history`).
      - Contexto (informativo, no entran al score): Beta y Market Cap en
        miles de millones de USD.

    También guarda el flujo de caja libre (o, si no está disponible, el
    operativo) como proxy de generación de caja, usado en el scoring del
    sector nuclear.

    NOTA: `Ticker.info` puede traer campos incompletos o nulos según el emisor;
    se manejan los `None` explícitamente para que la tabla y el score se
    calculen sin romper aunque falten datos — es el comportamiento
    esperado, no un error.
    """
    filas = []

    for simbolo in tickers:
        try:
            info = yf.Ticker(simbolo).info
        except Exception:
            info = {}

        flujo_caja = info.get("freeCashflow")
        if flujo_caja is None:
            flujo_caja = info.get("operatingCashflow")

        market_cap = info.get("marketCap")
        market_cap_b = round(market_cap / 1e9, 2) if market_cap is not None else None

        filas.append({
            "Ticker": simbolo,
            "P/E Trailing": info.get("trailingPE"),
            "P/E Forward": info.get("forwardPE"),
            "PEG Ratio": info.get("pegRatio"),
            "Price/Sales": info.get("priceToSalesTrailing12Months"),
            "Margen Bruto": info.get("grossMargins"),
            "Crecimiento Ingresos": info.get("revenueGrowth"),
            "ROE": info.get("returnOnEquity"),
            "Debt/Equity": info.get("debtToEquity"),
            "Dividend Yield": info.get("dividendYield"),
            "Momentum 3M (%)": _calcular_momentum_3m(simbolo),
            "Beta": info.get("beta"),
            "Market Cap (B USD)": market_cap_b,
            "Flujo de Caja (proxy)": flujo_caja,
        })

    return pd.DataFrame(filas).set_index("Ticker")

# --- SCORING DINÁMICO ---------------------------------------------------------

def _normalizar_columna(serie: pd.Series, menor_es_mejor: bool) -> pd.Series:
    """
    Normaliza una columna de métricas crudas a una escala 0-100 comparable,
    usando min-max scaling sobre los valores disponibles del sector:

      - Si "mayor es mejor" (ej. margen, crecimiento): el máximo del sector
        vale 100 y el mínimo vale 0.
      - Si "menor es mejor" (ej. P/E, P/S, Debt/Equity): se invierte la
        escala — el mínimo del sector vale 100 y el máximo vale 0.

    Los `None`/NaN se preservan como NaN (no se imputan): el llamador decide
    cómo redistribuir el peso de las métricas faltantes. Si todos los
    valores válidos del sector son iguales, se asigna 50.0 a los presentes
    para no favorecer arbitrariamente a ningún ticker.
    """
    valores = pd.to_numeric(serie, errors="coerce")
    validos = valores.dropna()

    if validos.empty:
        return pd.Series([float("nan")] * len(serie), index=serie.index)

    minimo, maximo = validos.min(), validos.max()

    if minimo == maximo:
        return valores.apply(lambda v: 50.0 if pd.notna(v) else float("nan"))

    escala = (valores - minimo) / (maximo - minimo) * 100
    return 100 - escala if menor_es_mejor else escala


def calcular_score_sectorial(metricas: pd.DataFrame, sector: str) -> pd.DataFrame:
    """
    Calcula un score 0-100 por ticker combinando sub-scores normalizados de
    cada métrica con la tabla de pesos del sector. Devuelve `metricas` con
    columnas adicionales `<Métrica> (sub-score)` y `Score Sectorial`.

    Manejo de datos faltantes: si una métrica no tiene valor para un
    ticker, se excluye del promedio ponderado de ESE ticker y su peso se
    redistribuye proporcionalmente entre las métricas disponibles (en vez
    de penalizar al ticker por un dato que Yahoo simplemente no reportó).
    Si NINGUNA métrica tiene datos para un ticker, su score queda en `None`.

    Penalización por caja (solo sector "Nuclear/Uranio"): a las empresas
    sin generación de caja positiva (`Flujo de Caja (proxy)` <= 0 o
    ausente) se les resta `PENALIZACION_CAJA_NUCLEAR` puntos al score
    final, reflejando el riesgo de financiamiento típico de mineras/
    exploradoras de uranio.
    """
    pesos = PESOS_POR_SECTOR.get(sector, PESOS_POR_SECTOR["_default"])
    columnas_metricas = list(METRICAS_MENOR_ES_MEJOR.keys())

    resultado = metricas.copy()
    sub_scores = pd.DataFrame(index=metricas.index)

    for columna in columnas_metricas:
        sub = _normalizar_columna(metricas[columna], METRICAS_MENOR_ES_MEJOR[columna])
        sub_scores[columna] = sub
        resultado[f"{columna} (sub-score)"] = sub.round(1)

    scores_finales = []
    for ticker in metricas.index:
        fila_sub = sub_scores.loc[ticker].dropna()

        if fila_sub.empty:
            scores_finales.append(None)
            continue

        peso_disponible = sum(pesos.get(m, 0.0) for m in fila_sub.index)
        if peso_disponible == 0:
            score = fila_sub.mean()
        else:
            score = sum(fila_sub[m] * pesos.get(m, 0.0) for m in fila_sub.index) / peso_disponible

        if sector == "Nuclear/Uranio":
            flujo = metricas.loc[ticker, "Flujo de Caja (proxy)"]
            if flujo is None or flujo <= 0:
                score = max(0.0, score - PENALIZACION_CAJA_NUCLEAR)

        scores_finales.append(round(float(score), 1))

    resultado["Score Sectorial"] = scores_finales
    return resultado

# --- GANADOR Y VEREDICTO -------------------------------------------------------

def obtener_ganador_sectorial(scores: pd.DataFrame) -> dict | None:
    """
    Devuelve un diccionario con los datos del ticker de mayor `Score
    Sectorial` (ticker, score y sus métricas clave) para mostrar en
    `st.metric`, o `None` si ningún ticker del sector tiene score
    calculable.
    """
    validos = scores.dropna(subset=["Score Sectorial"])
    if validos.empty:
        return None

    fila = validos.loc[validos["Score Sectorial"].idxmax()]
    return {
        "ticker": fila.name,
        "score": fila["Score Sectorial"],
        "pe_trailing": fila["P/E Trailing"],
        "peg_ratio": fila["PEG Ratio"],
        "margen_bruto": fila["Margen Bruto"],
        "crecimiento_ingresos": fila["Crecimiento Ingresos"],
        "momentum_3m": fila["Momentum 3M (%)"],
    }


def _comentario_momentum(momentum: float | None) -> str:
    """
    Frase corta que cruza el momentum técnico (variación de precio a 3
    meses) con el veredicto fundamental: si el precio acompaña la tesis
    (momentum positivo) la confirma; si va en contra (negativo), advierte
    que el mercado todavía no lo está validando — útil para timing de entrada.
    """
    if momentum is None:
        return "No hay datos de momentum de precio para confirmar la tendencia reciente."
    if momentum > 5:
        return f"El precio además acompaña la tesis: sube **{momentum:+.1f}%** en 3 meses, confirmando el momentum."
    if momentum < -5:
        return f"Ojo: el precio cae **{momentum:+.1f}%** en 3 meses — el mercado todavía no convalida esta historia."
    return f"El precio se mantiene relativamente estable (**{momentum:+.1f}%** en 3 meses), sin una tendencia marcada que confirme o contradiga la tesis."


def generar_veredicto(ganador: dict | None, sector: str) -> str:
    """
    Redacta un párrafo en español que cruza el score del ganador del sector
    con su nivel de valuación (P/E trailing) para emitir un veredicto
    cualitativo del Asistente Quant, y le agrega una lectura del momentum
    de precio reciente (3 meses) como confirmación o advertencia técnica:

      - Score alto (>= 70) + P/E elevado (> 30): alcista con cautela —
        la calidad es real pero el precio ya la refleja en gran parte.
      - Score alto (>= 70) + P/E razonable (<= 30) o sin dato: señal de
        compra fuerte — fundamentos sólidos a un múltiplo no exigente.
      - Score medio (40-70): mixto — esperar confirmación o profundizar
        el análisis cualitativo antes de tomar posición.
      - Score bajo (< 40): evitar — el balance de métricas del sector no
        favorece a este nombre frente a sus pares.

    Si no hay ganador calculable (sin datos), devuelve un mensaje
    indicando que Yahoo Finance no proveyó información suficiente.
    """
    if ganador is None:
        return (
            f"No fue posible calcular un veredicto para el sector "
            f"**{sector}**: Yahoo Finance no devolvió métricas suficientes "
            f"para ninguno de los tickers analizados."
        )

    ticker, score, pe = ganador["ticker"], ganador["score"], ganador["pe_trailing"]
    pe_texto = f"{pe:.1f}x" if pe is not None else "no disponible"
    comentario_momentum = _comentario_momentum(ganador["momentum_3m"])

    if score >= 70 and pe is not None and pe > 30:
        cuerpo = (
            f"**{ticker}** lidera el sector **{sector}** con un score de "
            f"**{score}/100**, respaldado por fundamentos sólidos. Sin embargo, "
            f"su P/E trailing de {pe_texto} sugiere una valuación exigente: "
            f"el mercado ya está pagando por ese liderazgo. Veredicto: "
            f"**alcista con cautela** — calidad confirmada, pero conviene "
            f"esperar una mejora en el punto de entrada antes de aumentar exposición."
        )
    elif score >= 70:
        cuerpo = (
            f"**{ticker}** lidera el sector **{sector}** con un score de "
            f"**{score}/100** y una valuación razonable (P/E trailing de "
            f"{pe_texto}). Esta combinación de fundamentos sólidos a un "
            f"múltiplo no exigente es la que busca un quant. Veredicto: "
            f"**señal de compra fuerte**."
        )
    elif score >= 40:
        cuerpo = (
            f"**{ticker}** se posiciona como el mejor del sector **{sector}**, "
            f"pero con un score de **{score}/100** que refleja un perfil mixto: "
            f"ni domina claramente a sus pares ni presenta señales de alarma. "
            f"Veredicto: **mantener en observación** — conviene profundizar el "
            f"análisis cualitativo antes de tomar una posición relevante."
        )
    else:
        cuerpo = (
            f"Incluso el mejor posicionado del sector **{sector}**, **{ticker}**, "
            f"obtiene un score bajo de **{score}/100**, lo que indica que el "
            f"sector en su conjunto no muestra una combinación atractiva de "
            f"valuación, rentabilidad y solidez financiera en este momento. "
            f"Veredicto: **evitar exposición** hasta que mejoren los fundamentos "
            f"relativos."
        )

    return f"{cuerpo} {comentario_momentum}"

# --- ESTILO DE TABLA -----------------------------------------------------------

def estilo_mejores_ratios(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    """
    Aplica estilo condicional al DataFrame de métricas: resalta en verde
    (paleta `#1b4332`/`#a8dadc`, acorde al tema oscuro `#1a1a2e`) la celda
    con el mejor valor de cada columna de métrica (mínimo si "menor es
    mejor", máximo si "mayor es mejor"), y en rojo tenue (`#4a1c2b`/
    `#e94560`) la celda con el peor valor. Las columnas de sub-score y el
    score final no se estilizan por columna para no saturar la tabla.
    """
    color_mejor = "background-color: #1b4332; color: #a8dadc; font-weight: 600;"
    color_peor = "background-color: #4a1c2b; color: #e94560;"

    def _resaltar_columna(serie: pd.Series) -> list:
        valores = pd.to_numeric(serie, errors="coerce")
        if valores.dropna().empty:
            return ["" for _ in serie]

        menor_es_mejor = METRICAS_MENOR_ES_MEJOR.get(serie.name, False)
        mejor = valores.min() if menor_es_mejor else valores.max()
        peor = valores.max() if menor_es_mejor else valores.min()

        estilos = []
        for v in valores:
            if pd.isna(v):
                estilos.append("")
            elif mejor != peor and v == mejor:
                estilos.append(color_mejor)
            elif mejor != peor and v == peor:
                estilos.append(color_peor)
            else:
                estilos.append("")
        return estilos

    columnas_a_resaltar = list(METRICAS_MENOR_ES_MEJOR.keys())

    return (
        df.style
        .apply(_resaltar_columna, subset=columnas_a_resaltar)
        .format(precision=2, na_rep="—")
    )
