"""
pdf_generator.py
================
Generacion del reporte institucional en PDF (estilo banco de inversion).

  - Plantilla HTML/CSS minimalista en azul marino / gris.
  - Motor WeasyPrint para renderizar a PDF.
  - Nombre dinamico: Quant_Research_YYYY_MM_DD.pdf
  - Manejo de excepciones visuales: cualquier dato faltante se muestra como
    "N/A" (jamas crashea ni muestra "0%" enganioso).

Nota Windows: WeasyPrint requiere las librerias nativas GTK/Pango/Cairo. Si no
estan instaladas, este modulo cae a un fallback que escribe el HTML a disco y
deja un PDF placeholder, dejando un log claro con instrucciones de instalacion.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any, Dict, List, Optional

log = logging.getLogger("quant_bot.pdf")

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "outputs", "reports")


# ---------------------------------------------------------------------------
# Formateadores tolerantes a None  -> "N/A"
# ---------------------------------------------------------------------------
def fmt_pct(x: Optional[float], decimals: int = 1) -> str:
    """Formatea una fraccion (0.153) como porcentaje. None -> 'N/A'."""
    if x is None:
        return "N/A"
    try:
        return f"{x * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def fmt_num(x: Optional[float], decimals: int = 2) -> str:
    if x is None:
        return "N/A"
    try:
        return f"{x:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_money(x: Optional[float]) -> str:
    """Formatea montos grandes con sufijos B/M. None -> 'N/A'."""
    if x is None:
        return "N/A"
    try:
        ax = abs(x)
        if ax >= 1e9:
            return f"${x / 1e9:,.2f}B"
        if ax >= 1e6:
            return f"${x / 1e6:,.2f}M"
        return f"${x:,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def _yesno(b: Optional[bool]) -> str:
    if b is None:
        return "N/A"
    return "SI" if b else "NO"


def _badge(passed: Optional[bool], evaluable: bool = True) -> str:
    if not evaluable or passed is None:
        return '<span class="badge na">N/A</span>'
    cls = "pass" if passed else "fail"
    txt = "PASA" if passed else "NO"
    return f'<span class="badge {cls}">{txt}</span>'


# ---------------------------------------------------------------------------
# Construccion del HTML
# ---------------------------------------------------------------------------
def _build_summary_rows(records: List[Dict[str, Any]]) -> str:
    rows = []
    for i, d in enumerate(records, 1):
        dcf = d.get("dcf") or {}
        mos = dcf.get("margin_of_safety") if dcf.get("evaluable") else None
        mos_cls = ""
        if mos is not None:
            mos_cls = "pos" if mos > 0 else "neg"
        rows.append(f"""
        <tr>
          <td class="rank">{i}</td>
          <td class="ticker">{d.get('ticker', 'N/A')}</td>
          <td class="name">{d.get('name', 'N/A')}</td>
          <td>{d.get('sector_bucket', 'N/A')}</td>
          <td class="num">{fmt_money(d.get('market_cap'))}</td>
          <td class="center">{_badge(d.get('buffett', {}).get('passed'), d.get('buffett', {}).get('evaluable', False))}</td>
          <td class="center">{_badge(d.get('lynch', {}).get('passed'), d.get('lynch', {}).get('evaluable', False))}</td>
          <td class="num">{fmt_money(dcf.get('target_price')) if dcf.get('evaluable') else 'N/A'}</td>
          <td class="num {mos_cls}">{fmt_pct(mos)}</td>
          <td class="num">{fmt_num(d.get('sentiment', {}).get('score'), 2)}</td>
          <td class="num score">{fmt_num(d.get('score'), 1)}</td>
        </tr>""")
    return "".join(rows)


def _build_detail_cards(records: List[Dict[str, Any]]) -> str:
    cards = []
    for d in records:
        buffett = d.get("buffett", {})
        lynch = d.get("lynch", {})
        dcf = d.get("dcf") or {}
        gem = d.get("gem", {})
        sent = d.get("sentiment", {})

        headlines_html = "".join(
            f"<li>{h}</li>" for h in (sent.get("headlines") or [])
        ) or "<li>Sin titulares recientes.</li>"

        dcf_block = (
            f"""
            <div class="dcf-grid">
              <div><span>FCF base</span><b>{fmt_money(dcf.get('fcf_base'))}</b></div>
              <div><span>Crecimiento</span><b>{fmt_pct(dcf.get('growth_rate'))}</b></div>
              <div><span>Tasa descuento</span><b>{fmt_pct(dcf.get('discount_rate'))}</b></div>
              <div><span>Enterprise Value</span><b>{fmt_money(dcf.get('enterprise_value'))}</b></div>
              <div><span>Deuda Neta real</span><b>{fmt_money(dcf.get('net_debt'))}</b></div>
              <div><span>Equity Value</span><b>{fmt_money(dcf.get('equity_value'))}</b></div>
              <div><span>Precio actual</span><b>{fmt_num(dcf.get('current_price'))}</b></div>
              <div><span>Precio Objetivo</span><b>{fmt_num(dcf.get('target_price'))}</b></div>
              <div class="full"><span>Margen de Seguridad</span>
                <b class="{('pos' if (dcf.get('margin_of_safety') or 0) > 0 else 'neg') if dcf.get('margin_of_safety') is not None else ''}">
                {fmt_pct(dcf.get('margin_of_safety'))}</b></div>
            </div>"""
            if dcf.get("evaluable")
            else '<p class="muted">DCF no evaluable (FCF o acciones no disponibles). Valor: N/A.</p>'
        )

        cards.append(f"""
        <div class="card">
          <div class="card-head">
            <h3>{d.get('ticker', 'N/A')} &middot; {d.get('name', 'N/A')}</h3>
            <div class="score-pill">Score {fmt_num(d.get('score'), 1)}</div>
          </div>
          <div class="card-meta">
            {d.get('sector_bucket', 'N/A')} | {d.get('industry') or 'N/A'} |
            Cap: {fmt_money(d.get('market_cap'))} | Precio: {fmt_num(d.get('price'))} {d.get('currency','')}
          </div>

          <div class="metrics">
            <div class="metric-col">
              <h4>Filtro Buffett {_badge(buffett.get('passed'), buffett.get('evaluable', False))}</h4>
              <ul>
                <li>ROE: {fmt_pct(buffett.get('roe'))} <small>(req &gt;15%)</small></li>
                <li>Deuda/Capital: {fmt_num(buffett.get('debt_to_equity'))}x <small>(req &lt;1.0)</small></li>
              </ul>
            </div>
            <div class="metric-col">
              <h4>Filtro Lynch {_badge(lynch.get('passed'), lynch.get('evaluable', False))}</h4>
              <ul>
                <li>PEG: {fmt_num(lynch.get('peg'))} <small>(req &lt;1.0)</small></li>
                <li>Crec. Ventas: {fmt_pct(lynch.get('revenue_growth'))} <small>(req &gt;15%)</small></li>
              </ul>
            </div>
            <div class="metric-col">
              <h4>Calidad / Joyita</h4>
              <ul>
                <li>Margen Bruto: {fmt_pct(d.get('gross_margin'))}</li>
                <li>Margen Op.: {fmt_pct(d.get('operating_margin'))}</li>
                <li>Insiders: {fmt_pct(gem.get('insider_pct'))}</li>
                <li>Small-cap gem: {_yesno(gem.get('is_gem'))}</li>
              </ul>
            </div>
          </div>

          <h4 class="section-sub">Valuacion DCF (Caso Base, 5 anios)</h4>
          {dcf_block}

          <h4 class="section-sub">Sentimiento Social: {fmt_num(sent.get('score'), 2)}
            <small>({sent.get('n_headlines', 0)} titulares)</small></h4>
          <ul class="headlines">{headlines_html}</ul>
        </div>""")
    return "".join(cards)


def build_html(records: List[Dict[str, Any]], report_date: date) -> str:
    """Construye el documento HTML completo del reporte."""
    n = len(records)
    n_buffett = sum(1 for d in records if d.get("buffett", {}).get("passed"))
    n_lynch = sum(1 for d in records if d.get("lynch", {}).get("passed"))
    n_gems = sum(1 for d in records if d.get("gem", {}).get("is_gem"))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: A4;
    margin: 1.8cm 1.5cm;
    @bottom-center {{
      content: "Quant Research \\2014 Confidencial \\2014 Pagina " counter(page) " de " counter(pages);
      font-size: 8px; color: #8a94a6;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Helvetica Neue", Arial, sans-serif;
    color: #2b2f38; font-size: 10px; line-height: 1.45; margin: 0;
  }}
  .cover {{ border-bottom: 3px solid #c9a227; padding-bottom: 16px; margin-bottom: 22px; }}
  .cover .kicker {{ color: #c9a227; letter-spacing: 3px; font-size: 9px; font-weight: 700; }}
  .cover h1 {{ color: #0f2747; font-size: 26px; margin: 6px 0 2px; }}
  .cover .date {{ color: #6b7280; font-size: 11px; }}

  .summary-cards {{ display: flex; gap: 10px; margin: 18px 0 24px; }}
  .summary-cards .box {{
    flex: 1; background: #0f2747; color: #fff; border-radius: 6px; padding: 12px;
  }}
  .summary-cards .box .v {{ font-size: 22px; font-weight: 700; color: #c9a227; }}
  .summary-cards .box .l {{ font-size: 8px; letter-spacing: 1px; text-transform: uppercase; opacity: .8; }}

  h2.section {{
    color: #0f2747; font-size: 14px; border-left: 4px solid #c9a227;
    padding-left: 8px; margin: 26px 0 12px;
  }}

  table {{ width: 100%; border-collapse: collapse; font-size: 9px; }}
  thead th {{
    background: #0f2747; color: #fff; padding: 7px 5px; text-align: left;
    font-weight: 600; font-size: 8px; text-transform: uppercase; letter-spacing: .3px;
  }}
  tbody td {{ padding: 6px 5px; border-bottom: 1px solid #e5e8ee; }}
  tbody tr:nth-child(even) {{ background: #f6f8fb; }}
  td.num, th.num {{ text-align: right; }}
  td.center {{ text-align: center; }}
  td.rank {{ color: #8a94a6; font-weight: 700; }}
  td.ticker {{ font-weight: 700; color: #0f2747; }}
  td.score {{ font-weight: 700; color: #0f2747; }}
  .pos {{ color: #1a7f4b; font-weight: 600; }}
  .neg {{ color: #b3261e; font-weight: 600; }}

  .badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 8px; font-weight: 700; }}
  .badge.pass {{ background: #d8f0e2; color: #1a7f4b; }}
  .badge.fail {{ background: #f6dcd9; color: #b3261e; }}
  .badge.na {{ background: #e9ecf2; color: #8a94a6; }}

  .card {{ border: 1px solid #e0e4ec; border-radius: 6px; padding: 14px; margin-bottom: 14px; page-break-inside: avoid; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: center; }}
  .card-head h3 {{ color: #0f2747; margin: 0; font-size: 13px; }}
  .score-pill {{ background: #0f2747; color: #c9a227; padding: 3px 10px; border-radius: 12px; font-size: 9px; font-weight: 700; }}
  .card-meta {{ color: #6b7280; font-size: 8.5px; margin: 4px 0 10px; }}
  .metrics {{ display: flex; gap: 14px; }}
  .metric-col {{ flex: 1; }}
  .metric-col h4 {{ font-size: 10px; color: #0f2747; margin: 0 0 5px; }}
  .metric-col ul {{ list-style: none; padding: 0; margin: 0; }}
  .metric-col li {{ padding: 2px 0; border-bottom: 1px dotted #e5e8ee; }}
  .metric-col small {{ color: #9aa3b2; }}
  .section-sub {{ color: #0f2747; font-size: 10px; margin: 12px 0 6px; border-top: 1px solid #eef1f6; padding-top: 8px; }}
  .dcf-grid {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .dcf-grid > div {{ width: calc(33.33% - 6px); background: #f6f8fb; border-radius: 4px; padding: 6px 8px; }}
  .dcf-grid > div.full {{ width: 100%; background: #fdf6e3; }}
  .dcf-grid span {{ display: block; font-size: 8px; color: #8a94a6; text-transform: uppercase; letter-spacing: .3px; }}
  .dcf-grid b {{ font-size: 11px; color: #0f2747; }}
  .headlines {{ font-size: 8.5px; color: #4b5563; margin: 4px 0 0; padding-left: 16px; }}
  .muted {{ color: #9aa3b2; font-style: italic; }}
  .disclaimer {{ margin-top: 26px; font-size: 7.5px; color: #9aa3b2; border-top: 1px solid #e5e8ee; padding-top: 8px; }}
</style>
</head>
<body>
  <div class="cover">
    <div class="kicker">QUANT EQUITY RESEARCH</div>
    <h1>Reporte Semanal de Inversiones</h1>
    <div class="date">Fecha de cierre: {report_date.strftime('%d de %B de %Y')}</div>
  </div>

  <div class="summary-cards">
    <div class="box"><div class="v">{n}</div><div class="l">Empresas analizadas</div></div>
    <div class="box"><div class="v">{n_buffett}</div><div class="l">Pasan Buffett</div></div>
    <div class="box"><div class="v">{n_lynch}</div><div class="l">Pasan Lynch</div></div>
    <div class="box"><div class="v">{n_gems}</div><div class="l">Joyitas small-cap</div></div>
  </div>

  <h2 class="section">Ranking del Universo</h2>
  <table>
    <thead>
      <tr>
        <th class="num">#</th><th>Ticker</th><th>Empresa</th><th>Sector</th>
        <th class="num">Market Cap</th><th>Buffett</th><th>Lynch</th>
        <th class="num">P. Objetivo</th><th class="num">Margen Seg.</th>
        <th class="num">Sentim.</th><th class="num">Score</th>
      </tr>
    </thead>
    <tbody>{_build_summary_rows(records)}</tbody>
  </table>

  <h2 class="section">Analisis Detallado por Empresa</h2>
  {_build_detail_cards(records)}

  <div class="disclaimer">
    Documento generado automaticamente por Quant Bot con fines informativos y
    educativos. No constituye recomendacion de inversion. Datos provistos por
    Yahoo Finance (yfinance); pueden contener errores o retrasos. Los modelos DCF
    y los filtros son estimaciones simplificadas. "N/A" indica datos no disponibles.
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Render a PDF
# ---------------------------------------------------------------------------
def generate_pdf(records: List[Dict[str, Any]], report_date: Optional[date] = None) -> str:
    """
    Genera el PDF y devuelve la ruta absoluta del archivo.

    Si WeasyPrint no esta disponible (tipico en Windows sin GTK), guarda el HTML
    como fallback y devuelve esa ruta, dejando un log con la solucion.
    """
    report_date = report_date or date.today()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    stamp = report_date.strftime("%Y_%m_%d")
    pdf_path = os.path.join(REPORTS_DIR, f"Quant_Research_{stamp}.pdf")
    html_path = os.path.join(REPORTS_DIR, f"Quant_Research_{stamp}.html")

    html = build_html(records, report_date)

    # Siempre guardamos el HTML (sirve de respaldo y debug)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    try:
        from weasyprint import HTML  # import perezoso: solo si esta instalado
        HTML(string=html).write_pdf(pdf_path)
        log.info("PDF generado: %s", pdf_path)
        return pdf_path
    except Exception as exc:
        log.error(
            "WeasyPrint no pudo generar el PDF (%s). Se usa el HTML como fallback: %s. "
            "En Windows instala GTK3 (https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer) "
            "o ejecuta en WSL/Linux para PDF nativo.",
            exc, html_path,
        )
        return html_path
