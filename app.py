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

from modules import macro, technical, fundamental, ui_components

# --- CONFIGURACIÓN DE PÁGINA --------------------------------------------------

st.set_page_config(
    page_title="Asistente Cuantitativo Personal",
    page_icon="📊",
    layout="wide",
)

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
# MÓDULO 3 — Análisis Fundamental
# =============================================================================

st.subheader("🏦 Módulo 3 — Análisis Fundamental (Bancos)")
st.caption("Ratios de liquidez, apalancamiento (Debt/Equity) y P/E del último balance disponible en Yahoo Finance.")

tabla_fundamental = fundamental.obtener_metricas_fundamentales()
st.dataframe(tabla_fundamental, use_container_width=True)
