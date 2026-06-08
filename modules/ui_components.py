# =============================================================================
# Módulo 4 (helpers de UI) — Componentes reutilizables del dashboard
# =============================================================================

import streamlit as st

# --- CONFIGURACIÓN -----------------------------------------------------------

EMOJI_SEMAFORO = {
    "verde": "🟢",
    "amarillo": "🟡",
    "rojo": "🔴",
}

# --- ESTILOS GLOBALES (look futurista, sobre la paleta navy/rojo/teal) -------

ESTILOS_FUTURISTAS = """
<style>
/* Fondo con resplandores radiales neutros (blanco/gris) tipo HUD, sobre el navy base */
.stApp {
    background:
        radial-gradient(circle at 15% 10%, rgba(255, 255, 255, 0.045), transparent 35%),
        radial-gradient(circle at 85% 90%, rgba(255, 255, 255, 0.03), transparent 35%),
        #1a1a2e;
}

/* Títulos con degradé animado tipo "metal cepillado" (grises/plateados, sin color) */
h1, h2, h3 {
    background: linear-gradient(90deg, #d6d6e0, #84849a, #d6d6e0);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: acuant-degrade 9s linear infinite;
}

@keyframes acuant-degrade {
    0%   { background-position: 0% center; }
    100% { background-position: 200% center; }
}

/* Tarjetas de métricas (st.metric) con borde que brilla (gris/blanco) al pasar el mouse */
div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.04);
    transition: all 0.25s ease-in-out;
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(255, 255, 255, 0.35);
    box-shadow: 0 0 18px rgba(255, 255, 255, 0.15);
    transform: translateY(-2px);
}

/* Separadores (st.divider) como línea de "escaneo" gris degradada y animada */
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35), transparent);
    background-size: 200% auto;
    animation: acuant-barrido 6s ease-in-out infinite;
}

@keyframes acuant-barrido {
    0%   { background-position: 0% center; }
    50%  { background-position: 100% center; }
    100% { background-position: 0% center; }
}

/* Tablas (st.dataframe) con borde sutil y esquinas redondeadas */
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 0 14px rgba(0, 0, 0, 0.5);
}

/* Sidebar con degradé vertical sutil para reforzar la sensación de "panel" */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #20203c 0%, #1a1a2e 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Botones con glow neutro (blanco/gris) al hacer foco/hover */
button[kind] {
    transition: box-shadow 0.2s ease-in-out, transform 0.2s ease-in-out;
}
button[kind]:hover {
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.22);
    transform: translateY(-1px);
}
</style>
"""


def inyectar_estilos_futuristas():
    """
    Inyecta CSS global que le da al dashboard una estética "futurista" pero
    sobria: degradés animados en grises/plateados (look "metal cepillado"),
    resplandores neutros en tarjetas de métricas, separadores y paneles —
    todo en blanco/gris sobre el navy `#1a1a2e` base, SIN tonos de color.
    Los semáforos (🟢🟡🔴) y el resaltado verde/rojo de mejores/peores
    ratios en el screener (`screener.estilo_mejores_ratios`) son la
    excepción intencional: mantienen su significado funcional intacto.
    """
    st.markdown(ESTILOS_FUTURISTAS, unsafe_allow_html=True)

# --- SEMÁFOROS ----------------------------------------------------------------

def render_semaforo(nombre: str, valor, estado: str, columna=st):
    """
    Renderiza una métrica con badge de semáforo (🟢/🟡/🔴) usando st.metric.
    `valor` puede ser un precio, una variación %, un nivel, etc; se muestra
    tal cual lo reciba (como string ya formateado por el caller).
    """
    emoji = EMOJI_SEMAFORO.get(estado, "⚪")
    columna.metric(label=f"{emoji} {nombre}", value=valor)


def render_banner_global(estado: str):
    """
    Muestra un banner destacado con el veredicto macro global, indicando si
    el contexto ayuda o perjudica a un trade long en Argentina.
    """
    emoji = EMOJI_SEMAFORO.get(estado, "⚪")
    mensajes = {
        "verde": "Contexto macro FAVORABLE para long en Argentina",
        "amarillo": "Contexto macro NEUTRAL — mixto, operar con cautela",
        "rojo": "Contexto macro DESFAVORABLE para long en Argentina",
    }
    texto = mensajes.get(estado, "Contexto macro indeterminado")

    if estado == "verde":
        st.success(f"{emoji} {texto}")
    elif estado == "rojo":
        st.error(f"{emoji} {texto}")
    else:
        st.warning(f"{emoji} {texto}")
