from __future__ import annotations

from datetime import datetime

import streamlit as st
from googleapiclient.errors import HttpError

from ..config import DEFAULT_REISEAPOTHEKE
from ..google.calendar_service import create_event
from ..google.gmail_service import send_html_email
from ..models import Adventure


def render_adventure_details(
    adventure: Adventure,
    expanded: bool = False,
    key_prefix: str = "details",
) -> None:
    del expanded  # reserved for future UI behavior

    st.subheader(adventure.title)
    st.markdown(f"**Ort / Location:** {adventure.location}")
    st.markdown(f"**Dauer / Duration:** {adventure.duration}")

    st.markdown("### ✨ Tagesmotto / Daily motto")
    st.info(adventure.intro_quote)

    st.markdown("### 🧭 Die Idee / The idea")
    st.write(adventure.description)

    st.markdown("### 🎒 Vorbereitung / Preparation")
    for item in adventure.preparation:
        st.markdown(f"- {item}")

    st.markdown("### 🚶 Ablauf / Steps")
    for step in adventure.steps:
        st.markdown(f"- {step}")

    st.markdown("### 🧠 Warum gut für Carla? / Why this helps Carla")
    st.success(adventure.child_benefit)

    st.markdown("### 💡 Carla-Tipp des Tages / Carla's tip of the day")
    st.warning(adventure.carla_tip)

    st.markdown("### ⚠ Sicherheit / Safety")
    for risk in adventure.safety.risks:
        st.markdown(f"- **Risiko / Risk:** {risk}")

    st.markdown("**Prävention / Prevention:**")
    for prevention_item in adventure.safety.prevention:
        st.markdown(f"- {prevention_item}")

    st.markdown("### 🩹 Mini-Reiseapotheke / Mini travel first-aid kit")
    for item in DEFAULT_REISEAPOTHEKE:
        st.markdown(f"- {item}")

    cal_key = f"{key_prefix}-cal-{adventure.id}"
    mail_key = f"{key_prefix}-mail-{adventure.id}"

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📅 In Kalender eintragen / Add to calendar", key=cal_key):
            try:
                create_event(
                    title=adventure.title,
                    description=adventure.description,
                    start_time=datetime.now(),
                )
            except (HttpError, OSError, ValueError) as error:
                st.error(
                    f"Kalender-Eintrag fehlgeschlagen / Calendar entry failed: {error}"
                )
            else:
                st.success("Event erstellt! / Event created!")

    with col2:
        if st.button("📧 Per Mail senden / Send by email", key=mail_key):
            try:
                send_html_email(
                    to="gerrit.fabisch2024@gmail.com",
                    subject=f"Mikroabenteuer: {adventure.title}",
                    html_content=(
                        f"<h1>{adventure.title}</h1><p>{adventure.description}</p>"
                    ),
                )
            except (HttpError, OSError, ValueError) as error:
                st.error(f"Mail-Versand fehlgeschlagen / Email sending failed: {error}")
            else:
                st.success("Mail versendet! / Email sent!")
