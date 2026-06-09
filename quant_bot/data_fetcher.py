"""
data_fetcher.py
================
Extraccion de datos de mercado (yfinance) y analisis de sentimiento de noticias.

Responsabilidades:
  - Descargar fundamentals, balances y cash flows de un universo sectorial.
  - Manejar de forma defensiva los rate-limits y los cambios de schema de yfinance.
  - Leer titulares recientes y calcular un "Score de Sentimiento Social" via FinBERT.

Todas las funciones devuelven estructuras tolerantes a fallos: si un dato no
existe, se devuelve `None` (NUNCA se lanza la excepcion hacia arriba salvo que
sea irrecuperable). Asi el pipeline nunca crashea por un ticker malo.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

log = logging.getLogger("quant_bot.data")

# ---------------------------------------------------------------------------
# Motor de sentimiento financiero: FinBERT (HuggingFace transformers)
# ---------------------------------------------------------------------------
# Se carga de forma PEREZOSA: el modelo pesa ~400MB y tarda en bajar/instanciarse,
# asi que no queremos pagar ese costo al importar el modulo. Se instancia una sola
# vez y se cachea. Si transformers/torch no estan instalados, _FINBERT_FAILED queda
# en True y el sentimiento se reporta como "N/A" (nunca crashea el pipeline).
_FINBERT = None
_FINBERT_FAILED = False

# FinBERT devuelve etiquetas; las mapeamos a un valor numerico en [-1, +1].
_LABEL_TO_VALUE = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}


def _get_finbert():
    """Carga perezosa (y cacheada) del pipeline ProsusAI/finbert."""
    global _FINBERT, _FINBERT_FAILED
    if _FINBERT is not None or _FINBERT_FAILED:
        return _FINBERT
    try:
        from transformers import pipeline

        _FINBERT = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            truncation=True,
        )
        log.info("FinBERT (ProsusAI/finbert) cargado correctamente")
    except Exception as exc:  # transformers/torch no instalados o sin red al hub
        _FINBERT_FAILED = True
        log.error("No se pudo cargar FinBERT (sentimiento ira como N/A): %s", exc)
    return _FINBERT

# ---------------------------------------------------------------------------
# Universo de inversion: diccionario de sectores -> tickers
# ---------------------------------------------------------------------------
SECTORS: Dict[str, List[str]] = {
    "IA": ["NVDA", "MSFT", "GOOGL", "PLTR", "AMD"],
    "Fintech": ["MELI", "PYPL", "SOFI", "NU", "ADYEY"],
    "Energia": ["XOM", "CVX", "NEE", "ENPH", "FSLR"],
    "Mineria": ["BHP", "RIO", "FCX", "SCCO", "VALE"],
    # Joyitas reales: empresas con Market Cap en torno o por debajo de $2B.
    "Small-Caps & Growth": ["SPNS", "CRSR", "UPST", "HIMS", "MQ", "INMD", "DOCN", "BAND"],
}

# Cuantos reintentos hacemos cuando Yahoo nos tira rate-limit / red caida
_MAX_RETRIES = 3
_BACKOFF_SECONDS = 5


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _safe_get(d: Optional[Dict[str, Any]], key: str) -> Optional[float]:
    """Lee una clave numerica de un dict tolerando None / NaN / strings."""
    if not d:
        return None
    val = d.get(key)
    if val is None:
        return None
    try:
        f = float(val)
        if pd.isna(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _row(df: Optional[pd.DataFrame], *labels: str) -> Optional[float]:
    """
    Busca la primera etiqueta encontrada en el indice de un DataFrame de yfinance
    (balance/cashflow/financials) y devuelve el valor de la columna mas reciente.

    yfinance cambia los nombres de las filas seguido, por eso aceptamos varios
    alias y devolvemos el primero que matchee.
    """
    if df is None or df.empty:
        return None
    for label in labels:
        if label in df.index:
            try:
                series = df.loc[label].dropna()
                if not series.empty:
                    return float(series.iloc[0])  # columna mas reciente
            except Exception:
                continue
    return None


def _with_retries(fn, *, what: str):
    """Ejecuta `fn` con reintentos y backoff ante rate-limits de Yahoo."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as exc:  # yfinance no expone tipos claros de error
            last_exc = exc
            msg = str(exc).lower()
            is_rate = "rate" in msg or "too many" in msg or "429" in msg
            wait = _BACKOFF_SECONDS * attempt * (2 if is_rate else 1)
            log.warning(
                "Fallo al obtener %s (intento %d/%d): %s. Reintentando en %ds",
                what, attempt, _MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)
    log.error("Agotados los reintentos para %s: %s", what, last_exc)
    return None


# ---------------------------------------------------------------------------
# Extraccion de fundamentals
# ---------------------------------------------------------------------------
def get_fundamentals(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Descarga y normaliza los fundamentals de un ticker.

    Devuelve un dict con metricas crudas necesarias para los modelos
    (quant_models.py) o None si el ticker es irrecuperable.
    """
    def _fetch():
        t = yf.Ticker(ticker)
        info = t.info or {}
        balance = t.balance_sheet
        cashflow = t.cashflow
        financials = t.financials
        return t, info, balance, cashflow, financials

    bundle = _with_retries(_fetch, what=f"fundamentals de {ticker}")
    if bundle is None:
        return None
    _, info, balance, cashflow, financials = bundle

    # --- Cash flow / FCF -----------------------------------------------------
    op_cashflow = _row(cashflow, "Operating Cash Flow", "Total Cash From Operating Activities")
    capex = _row(cashflow, "Capital Expenditure", "Capital Expenditures")
    fcf = None
    if op_cashflow is not None and capex is not None:
        fcf = op_cashflow + capex  # capex viene negativo en yfinance
    if fcf is None:
        fcf = _safe_get(info, "freeCashflow")

    # --- Balance: deuda, leases, caja ---------------------------------------
    total_debt = _row(balance, "Total Debt") or _safe_get(info, "totalDebt")
    long_term_debt = _row(balance, "Long Term Debt", "LongTermDebt")
    short_term_debt = _row(balance, "Current Debt", "Short Long Term Debt")
    # Pasivos por arrendamientos financieros (financial leases)
    capital_leases = _row(
        balance,
        "Capital Lease Obligations",
        "Long Term Capital Lease Obligation",
        "Current Capital Lease Obligation",
    )
    cash = (
        _row(balance, "Cash And Cash Equivalents", "Cash And Cash Equivalents And Short Term Investments")
        or _safe_get(info, "totalCash")
    )

    data: Dict[str, Any] = {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency", "USD"),
        # Precio / mercado
        "price": _safe_get(info, "currentPrice") or _safe_get(info, "regularMarketPrice"),
        "market_cap": _safe_get(info, "marketCap"),
        "shares_outstanding": _safe_get(info, "sharesOutstanding"),
        "beta": _safe_get(info, "beta"),
        # Rentabilidad / multiplos
        "roe": _safe_get(info, "returnOnEquity"),
        "pe": _safe_get(info, "trailingPE"),
        "forward_pe": _safe_get(info, "forwardPE"),
        "peg": _safe_get(info, "pegRatio") or _safe_get(info, "trailingPegRatio"),
        "gross_margin": _safe_get(info, "grossMargins"),
        "operating_margin": _safe_get(info, "operatingMargins"),
        "profit_margin": _safe_get(info, "profitMargins"),
        "revenue_growth": _safe_get(info, "revenueGrowth"),
        "earnings_growth": _safe_get(info, "earningsGrowth"),
        "debt_to_equity": _safe_get(info, "debtToEquity"),  # yfinance lo da en %
        # Insiders (para el buscador de small caps)
        "insider_pct": _safe_get(info, "heldPercentInsiders"),
        # Bloques contables crudos (para el DCF)
        "fcf": fcf,
        "operating_cashflow": op_cashflow,
        "capex": capex,
        "total_debt": total_debt,
        "long_term_debt": long_term_debt,
        "short_term_debt": short_term_debt,
        "capital_leases": capital_leases,
        "cash": cash,
        "total_revenue": _row(financials, "Total Revenue") or _safe_get(info, "totalRevenue"),
    }
    log.info("Fundamentals OK: %s (%s)", ticker, data["name"])
    return data


# ---------------------------------------------------------------------------
# Sentimiento de noticias
# ---------------------------------------------------------------------------
def _fetch_headlines(ticker: str) -> List[str]:
    """Obtiene titulares recientes via yfinance.news (Yahoo) con fallback vacio."""
    def _fetch():
        return yf.Ticker(ticker).news or []

    raw = _with_retries(_fetch, what=f"noticias de {ticker}") or []
    headlines: List[str] = []
    for item in raw:
        # yfinance cambio el schema: a veces es {'title': ...},
        # a veces {'content': {'title': ...}}
        title = item.get("title")
        if not title and isinstance(item.get("content"), dict):
            title = item["content"].get("title")
        if title:
            headlines.append(title)
    return headlines


def get_news_sentiment(ticker: str) -> Dict[str, Any]:
    """
    Calcula el Score de Sentimiento Social (-1 a +1) corriendo los titulares
    recientes por FinBERT (ProsusAI/finbert), un modelo entrenado para finanzas.

    Cada titular se clasifica en positive/negative/neutral; lo mapeamos a
    +1/-1/0 y promediamos.

    Devuelve SIEMPRE un dict (nunca crashea). Cuando no hay datos o falla la
    inferencia, `score` es None y `status` es "N/A" -> el PDF muestra "N/A"
    (fmt_num(None) == "N/A") y quant_models trata None como neutro sin romper.
    """
    headlines = _fetch_headlines(ticker)
    if not headlines:
        log.warning("Sin titulares para %s; sentimiento N/A", ticker)
        return {"score": None, "status": "N/A", "n_headlines": 0, "headlines": []}

    nlp = _get_finbert()
    if nlp is None:
        log.warning("FinBERT no disponible; sentimiento N/A para %s", ticker)
        return {"score": None, "status": "N/A", "n_headlines": len(headlines), "headlines": headlines[:5]}

    # --- Inferencia protegida: si la API de Yahoo trajo basura o FinBERT falla,
    #     devolvemos N/A en vez de un 0.00 enganioso. ---------------------------
    try:
        results = nlp(headlines)
        values = [_LABEL_TO_VALUE.get(r["label"].lower(), 0.0) for r in results]
        avg = round(sum(values) / len(values), 3)
    except Exception as exc:
        log.error("Fallo la inferencia FinBERT para %s: %s", ticker, exc)
        return {"score": None, "status": "N/A", "n_headlines": len(headlines), "headlines": headlines[:5]}

    log.info("Sentimiento %s: %.3f sobre %d titulares (FinBERT)", ticker, avg, len(headlines))
    return {"score": avg, "status": "ok", "n_headlines": len(headlines), "headlines": headlines[:5]}


# ---------------------------------------------------------------------------
# Recoleccion del universo completo
# ---------------------------------------------------------------------------
def collect_universe(sectors: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, Any]]:
    """
    Recorre el diccionario de sectores y arma una lista de registros con
    fundamentals + sentimiento. Los tickers irrecuperables se omiten.
    """
    sectors = sectors or SECTORS
    records: List[Dict[str, Any]] = []
    for sector, tickers in sectors.items():
        for ticker in tickers:
            fundamentals = get_fundamentals(ticker)
            if fundamentals is None:
                log.warning("Omitido %s: sin fundamentals", ticker)
                continue
            fundamentals["sector_bucket"] = sector
            fundamentals["sentiment"] = get_news_sentiment(ticker)
            records.append(fundamentals)
            time.sleep(1)  # cortesia anti rate-limit entre tickers
    log.info("Universo recolectado: %d registros", len(records))
    return records
