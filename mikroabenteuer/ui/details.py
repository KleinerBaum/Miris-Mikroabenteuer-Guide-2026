import streamlit as st

from mikroabenteuer.config import DEFAULT_REISEAPOTHEKE
from mikroabenteuer.models import Adventure


def render_adventure_details(adventure: Adventure, expanded: bool = False) -> None:
    st.subheader(adventure.title)
    st.markdown(f"**Ort:** {adventure.location}")
    st.markdown(f"**Dauer:** {adventure.duration}")

    st.markdown("### ✨ Tagesmotto")
    st.info(adventure.intro_quote)

    st.markdown("### 🧭 Die Idee")
    st.write(adventure.description)

    st.markdown("### 🎒 Vorbereitung")
    for item in adventure.preparation:
        st.markdown(f"- {item}")

    st.markdown("### 🚶 Ablauf")
    for step in adventure.steps:
        st.markdown(f"- {step}")

    st.markdown("### 🧠 Warum gut für Carla?")
    st.success(adventure.child_benefit)

    st.markdown("### 💡 Carla-Tipp des Tages")
    st.warning(adventure.carla_tip)

    st.markdown("### ⚠ Sicherheit")
    for risk in adventure.safety.risks:
        st.markdown(f"- **Risiko:** {risk}")

    st.markdown("**Prävention:**")
    for prevention_item in adventure.safety.prevention:
        st.markdown(f"- {prevention_item}")

    st.markdown("### 🩹 Mini-Reiseapotheke")
    for item in DEFAULT_REISEAPOTHEKE:
        st.markdown(f"- {item}")
