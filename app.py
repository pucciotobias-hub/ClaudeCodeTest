# =============================================================================
# Asistente Cuantitativo Personal — Market Screener
# Dashboard interactivo (Streamlit) que combina contexto macro, análisis
# técnico multi-timeframe y análisis fundamental para apoyar decisiones de
# trading long en Argentina (GGAL / RFX20).
#
# Ejecutar con:  streamlit run app.py
# =============================================================================

import streamlit as st
import plotly.graph_objects as go

from modules import macro, technical, ui_components, screener

# --- CONFIGURACIÓN DE PÁGINA --------------------------------------------------

st.set_page_config(
    page_title="Asistente Cuantitativo Personal",
    page_icon="📊",
    layout="wide",
)

ui_components.inyectar_estilos_futuristas()

st.title("📊 Asistente Cuantitativo Personal")
st.caption("Termómetro macro + motor técnico MTF + análisis fundamental, en un solo screener.")

# --- SIDEBAR ------------------------------------------------------------------

TICKERS_DISPONIBLES = ["GGAL/JUN26", "RFX20/JUN26", "BMA"]

with st.sidebar:
    st.header("Configuración")
    ticker_seleccionado = st.selectbox("Ticker a analizar", TICKERS_DISPONIBLES)
    st.caption(
        "El Módulo 2 usa datos intradiarios de Yahoo Finance como proxy del "
        "instrumento elegido (ver comentario en `modules/technical.py` sobre "
        "cómo conectar pyRofex en vivo más adelante)."
    )

    st.divider()
    sector_seleccionado = st.selectbox("Sector a analizar (Screener)", list(screener.SECTORES.keys()))
    st.caption(
        "El Módulo 4 pondera cada métrica de forma distinta según el sector "
        "elegido (ej. tolera P/E alto en IA/Semiconductores, exige solidez "
        "de balance en Nuclear/Uranio)."
    )

# =============================================================================
# MÓDULO 1 — Contexto Macro (Termómetro Global)
# =============================================================================

st.subheader("🌍 Módulo 1 — Contexto Macro (Termómetro Global)")

contexto_macro = macro.obtener_contexto_macro()
estados_macro = macro.evaluar_semaforo(contexto_macro)
estado_global = macro.semaforo_global(estados_macro)

ui_components.render_banner_global(estado_global)

columnas_macro = st.columns(len(macro.TICKERS_MACRO))
for columna, (simbolo, nombre) in zip(columnas_macro, macro.TICKERS_MACRO.items()):
    fila = contexto_macro.loc[simbolo]
    if fila["precio"] is None:
        valor_mostrado = "Sin datos"
    else:
        valor_mostrado = f"{fila['precio']} ({fila['variacion_pct']:+.2f}%)"

    ui_components.render_semaforo(nombre, valor_mostrado, estados_macro[simbolo], columna=columna)

st.divider()

# =============================================================================
# MÓDULO 2 — Motor Técnico MTF
# =============================================================================

st.subheader(f"📈 Módulo 2 — Motor Técnico MTF · {ticker_seleccionado}")

datos_mtf = technical.obtener_datos_mtf(ticker_seleccionado)

col_tendencia, col_grafico = st.columns([1, 2])

with col_tendencia:
    st.markdown("**Tendencia por timeframe**")
    tabla_tendencia = technical.construir_tabla_tendencia_mtf(datos_mtf)
    st.dataframe(tabla_tendencia, hide_index=True, use_container_width=True)

    # Soporte/Resistencia y VWAP se calculan sobre el timeframe intradiario más fino
    df_intradia = datos_mtf.get("5 minutos")

    if df_intradia is not None and not df_intradia.empty:
        precio_actual = float(df_intradia["Close"].iloc[-1])
        soporte, resistencia = technical.detectar_soporte_resistencia(df_intradia)
        distancias = technical.calcular_distancia_sr(precio_actual, soporte, resistencia)

        st.markdown("**Soporte / Resistencia más cercanos**")
        st.metric("Soporte", soporte, delta=f"{distancias['dist_soporte_pct']}% desde el precio actual")
        st.metric("Resistencia", resistencia, delta=f"{distancias['dist_resistencia_pct']}% desde el precio actual")
    else:
        st.info("Sin datos intradiarios suficientes para calcular soporte/resistencia.")

with col_grafico:
    st.markdown("**Precio intradiario + VWAP (5 minutos)**")

    if df_intradia is not None and not df_intradia.empty:
        vwap = technical.calcular_vwap(df_intradia)

        figura = go.Figure()
        figura.add_trace(go.Scatter(x=df_intradia.index, y=df_intradia["Close"], name="Precio", line=dict(color="#a8dadc")))
        figura.add_trace(go.Scatter(x=df_intradia.index, y=vwap, name="VWAP", line=dict(color="#e94560", dash="dot")))
        figura.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(figura, use_container_width=True)
    else:
        st.info("Sin datos intradiarios disponibles para graficar.")

st.divider()

# =============================================================================
# MÓDULO 3 — Screener Sectorial Inteligente
# =============================================================================

st.subheader(f"🔬 Módulo 3 — Screener Sectorial Inteligente · {sector_seleccionado}")
st.caption(
    "Compara los tickers del sector elegido por valuación, rentabilidad y "
    "solidez financiera, y calcula un score 0-100 con ponderaciones "
    "específicas para el ADN de cada sector."
)

tickers_sector = screener.SECTORES[sector_seleccionado]
metricas_sector = screener.obtener_metricas_sectoriales(tickers_sector)
tabla_scores = screener.calcular_score_sectorial(metricas_sector, sector_seleccionado)

st.markdown("**Comparativa del sector** _(verde = mejor ratio, rojo = peor ratio de cada columna)_")
st.dataframe(screener.estilo_mejores_ratios(tabla_scores), use_container_width=True)

ganador = screener.obtener_ganador_sectorial(tabla_scores)

st.markdown("**🏆 El Ganador del Sector**")
if ganador is not None:
    col_ticker, col_score, col_pe, col_peg = st.columns(4)
    col_ticker.metric("Ticker", ganador["ticker"])
    col_score.metric("Score Sectorial", f"{ganador['score']}/100")
    col_pe.metric(
        "P/E Trailing",
        f"{ganador['pe_trailing']:.1f}x" if ganador["pe_trailing"] is not None else "Sin datos",
    )
    col_peg.metric(
        "PEG Ratio",
        f"{ganador['peg_ratio']:.2f}" if ganador["peg_ratio"] is not None else "Sin datos",
    )

    col_margen, col_crecimiento, col_momentum = st.columns(3)
    col_margen.metric(
        "Margen Bruto",
        f"{ganador['margen_bruto']:.1%}" if ganador["margen_bruto"] is not None else "Sin datos",
    )
    col_crecimiento.metric(
        "Crecimiento Ingresos",
        f"{ganador['crecimiento_ingresos']:.1%}" if ganador["crecimiento_ingresos"] is not None else "Sin datos",
    )
    col_momentum.metric(
        "Momentum 3M",
        f"{ganador['momentum_3m']:+.1f}%" if ganador["momentum_3m"] is not None else "Sin datos",
    )
else:
    st.info("Yahoo Finance no devolvió métricas suficientes para calcular un ganador en este sector.")

st.markdown("**🧠 Veredicto del Asistente Quant**")
st.markdown(screener.generar_veredicto(ganador, sector_seleccionado))
