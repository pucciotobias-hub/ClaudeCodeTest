"""
quant_models.py
===============
Motor matematico y contable.

Contiene:
  - Filtros de guru (Buffett, Peter Lynch).
  - Modelo DCF a 5 anios con rigor contable (deuda neta real incl. leases, FCF).
  - Buscador de "joyitas" small-cap con incremento de tenencia de insiders.
  - Scoring compuesto que ordena el universo.

Diseno defensivo: cada funcion tolera datos faltantes (None). Si falta un input
clave, el resultado correspondiente queda en None y el campo se reporta como
"N/A" aguas abajo, en vez de romper el pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("quant_bot.models")

# ---------------------------------------------------------------------------
# Parametros del modelo DCF (ajustables)
# ---------------------------------------------------------------------------
DCF_YEARS = 5
DEFAULT_DISCOUNT_RATE = 0.10      # WACC aproximado / tasa de descuento
DEFAULT_TERMINAL_GROWTH = 0.025   # crecimiento perpetuo (~inflacion LP)
MAX_FCF_GROWTH = 0.25             # cap al crecimiento para no inflar el DCF
MIN_FCF_GROWTH = 0.00


def _pct(x: Optional[float]) -> Optional[float]:
    """Normaliza ratios que yfinance a veces da en % (ej 45.0) a fraccion (0.45)."""
    if x is None:
        return None
    return x / 100.0 if abs(x) > 1.5 else x


# ---------------------------------------------------------------------------
# Filtros de guru
# ---------------------------------------------------------------------------
def buffett_filter(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtro Buffett: negocios rentables con poca deuda.
      - ROE > 15%
      - Deuda / Capital < 1.0
    debt_to_equity de yfinance viene en porcentaje (ej 80.0 == 0.80x).
    """
    roe = d.get("roe")
    de_raw = d.get("debt_to_equity")
    de = (de_raw / 100.0) if de_raw is not None else None

    checks = {
        "roe_gt_15": (roe is not None and roe > 0.15),
        "de_lt_1": (de is not None and de < 1.0),
    }
    passed = all(checks.values()) if all(v is not None for v in (roe, de)) else False
    return {
        "passed": passed,
        "checks": checks,
        "roe": roe,
        "debt_to_equity": de,
        "evaluable": roe is not None and de is not None,
    }


def lynch_filter(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtro Peter Lynch: crecimiento a precio razonable.
      - PEG < 1.0
      - Crecimiento de ventas > 15%
    """
    peg = d.get("peg")
    rev_growth = d.get("revenue_growth")

    checks = {
        "peg_lt_1": (peg is not None and 0 < peg < 1.0),
        "rev_growth_gt_15": (rev_growth is not None and rev_growth > 0.15),
    }
    passed = all(checks.values()) if all(v is not None for v in (peg, rev_growth)) else False
    return {
        "passed": passed,
        "checks": checks,
        "peg": peg,
        "revenue_growth": rev_growth,
        "evaluable": peg is not None and rev_growth is not None,
    }


# ---------------------------------------------------------------------------
# Rigor contable: deuda neta real
# ---------------------------------------------------------------------------
def net_debt(d: Dict[str, Any]) -> Optional[float]:
    """
    Calcula la deuda neta real normalizada:

        Deuda Neta = Deuda Financiera Total + Leases financieros - Caja

    Reconstruye la deuda total desde sus componentes si `total_debt` no esta
    disponible, e incorpora explicitamente los pasivos por arrendamiento
    financiero (financial leases) cuando existan.
    """
    total_debt = d.get("total_debt")
    if total_debt is None:
        lt = d.get("long_term_debt") or 0.0
        st = d.get("short_term_debt") or 0.0
        if lt or st:
            total_debt = lt + st

    if total_debt is None:
        return None

    leases = d.get("capital_leases") or 0.0
    cash = d.get("cash") or 0.0
    nd = total_debt + leases - cash
    return nd


# ---------------------------------------------------------------------------
# Modelo DCF a 5 anios
# ---------------------------------------------------------------------------
def dcf_model(
    d: Dict[str, Any],
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    terminal_growth: float = DEFAULT_TERMINAL_GROWTH,
) -> Optional[Dict[str, Any]]:
    """
    Flujo de Caja Descontado (Caso Base) a 5 anios.

    Pasos:
      1. Parte del Flujo de Caja Libre (FCF) operativo del ultimo ejercicio.
      2. Proyecta FCF con una tasa de crecimiento derivada (acotada).
      3. Descuenta los flujos + un valor terminal (Gordon).
      4. Equity Value = Enterprise Value - Deuda Neta real.
      5. Precio Objetivo = Equity Value / acciones; Margen de Seguridad vs precio.

    Devuelve None si faltan inputs criticos (FCF o acciones).
    """
    fcf = d.get("fcf")
    shares = d.get("shares_outstanding")
    price = d.get("price")

    if fcf is None or shares is None or shares <= 0:
        log.info("DCF no evaluable para %s (FCF o acciones faltantes)", d.get("ticker"))
        return None
    if fcf <= 0:
        log.info("DCF omitido para %s (FCF negativo: %.0f)", d.get("ticker"), fcf)
        return None

    # Tasa de crecimiento: usamos earnings/revenue growth acotado
    g = d.get("earnings_growth") or d.get("revenue_growth") or 0.05
    g = max(MIN_FCF_GROWTH, min(g, MAX_FCF_GROWTH))

    # 1-2. Proyeccion y descuento de los flujos explicitos
    pv_flows = 0.0
    projected: List[float] = []
    cf = fcf
    for year in range(1, DCF_YEARS + 1):
        cf = cf * (1 + g)
        pv = cf / ((1 + discount_rate) ** year)
        projected.append(cf)
        pv_flows += pv

    # 3. Valor terminal (Gordon Growth) descontado
    terminal_cf = projected[-1] * (1 + terminal_growth)
    terminal_value = terminal_cf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** DCF_YEARS)

    enterprise_value = pv_flows + pv_terminal

    # 4. Equity value usando deuda neta real
    nd = net_debt(d) or 0.0
    equity_value = enterprise_value - nd

    # 5. Precio objetivo y margen de seguridad
    target_price = equity_value / shares
    margin_of_safety = None
    if price and price > 0:
        margin_of_safety = (target_price - price) / price

    return {
        "evaluable": True,
        "fcf_base": fcf,
        "growth_rate": g,
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
        "enterprise_value": enterprise_value,
        "net_debt": nd,
        "equity_value": equity_value,
        "target_price": target_price,
        "current_price": price,
        "margin_of_safety": margin_of_safety,
        "projected_fcf": projected,
    }


# ---------------------------------------------------------------------------
# Buscador de joyitas (small caps)
# ---------------------------------------------------------------------------
GEM_MIN_MARKET_CAP = 300_000_000      # $300M
GEM_MAX_MARKET_CAP = 2_000_000_000    # $2B
GEM_MIN_INSIDER_PCT = 0.05            # >5% en manos de directivos


def is_small_cap_gem(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Marca candidatas a "joyita":
      - Market cap entre $300M y $2B.
      - Alta tenencia de insiders (proxy de conviccion de los directivos).

    Nota: yfinance no expone series historicas de insiders de forma confiable,
    asi que usamos `heldPercentInsiders` como proxy del nivel/incremento de
    tenencia. El umbral es configurable.
    """
    mc = d.get("market_cap")
    insider = d.get("insider_pct")

    in_range = mc is not None and GEM_MIN_MARKET_CAP <= mc <= GEM_MAX_MARKET_CAP
    high_insider = insider is not None and insider >= GEM_MIN_INSIDER_PCT
    return {
        "is_gem": bool(in_range and high_insider),
        "in_cap_range": in_range,
        "high_insider": high_insider,
        "market_cap": mc,
        "insider_pct": insider,
    }


# ---------------------------------------------------------------------------
# Scoring compuesto
# ---------------------------------------------------------------------------
def composite_score(d: Dict[str, Any]) -> float:
    """
    Score 0-100 que combina filtros de guru, margen de seguridad del DCF y
    sentimiento social. Usado para ordenar el ranking del reporte.
    """
    score = 0.0

    if d.get("buffett", {}).get("passed"):
        score += 25
    if d.get("lynch", {}).get("passed"):
        score += 25

    dcf = d.get("dcf")
    if dcf and dcf.get("margin_of_safety") is not None:
        mos = dcf["margin_of_safety"]
        # +30 si MoS >= 50%, escalado linealmente, 0 si negativo
        score += max(0.0, min(mos, 0.5)) / 0.5 * 30

    sent = d.get("sentiment", {}).get("score", 0.0) or 0.0
    score += (sent + 1) / 2 * 10  # 0..10

    if d.get("gem", {}).get("is_gem"):
        score += 10

    return round(score, 1)


def analyze(record: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica todos los modelos a un registro de fundamentals y lo enriquece."""
    record["buffett"] = buffett_filter(record)
    record["lynch"] = lynch_filter(record)
    record["dcf"] = dcf_model(record)
    record["gem"] = is_small_cap_gem(record)
    record["score"] = composite_score(record)
    return record


def run_models(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Corre los modelos sobre todo el universo y lo ordena por score desc."""
    analyzed = [analyze(r) for r in records]
    analyzed.sort(key=lambda r: r.get("score", 0), reverse=True)
    log.info("Modelos aplicados a %d registros", len(analyzed))
    return analyzed
