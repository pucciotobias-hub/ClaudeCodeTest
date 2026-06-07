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
