from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

from mikroabenteuer.config import DEFAULT_REISEAPOTHEKE
from mikroabenteuer.google.auth import OAuthConfigurationError
from mikroabenteuer.google.calendar_service import create_event
from mikroabenteuer.google.gmail_service import (
    build_daily_scheduler_email_html,
    build_ics_attachment,
    send_html_email,
)
from mikroabenteuer.google.schemas import CalendarEventInput, DailyDigestInput
from mikroabenteuer.models import Adventure


def render_adventure_details(
    adventure: Adventure,
    *,
    user_key: str | None,
    sender_email: str,
    expanded: bool = False,
) -> None:
    del expanded
    st.subheader(adventure.title)
    st.markdown(f"**Ort / Location:** {adventure.location}")
    st.markdown(f"**Dauer / Duration:** {adventure.duration}")

    st.markdown("### ✨ Tagesmotto / Daily Motto")
    st.info(adventure.intro_quote)

    st.markdown("### 🧭 Die Idee / The Idea")
    st.write(adventure.description)

    st.markdown("### 🎒 Vorbereitung / Preparation")
    for item in adventure.preparation:
        st.markdown(f"- {item}")

    st.markdown("### 🚶 Ablauf / Steps")
    for step in adventure.steps:
        st.markdown(f"- {step}")

    st.markdown("### 🧠 Warum gut für Carla? / Why it helps Carla")
    st.success(adventure.child_benefit)

    st.markdown("### 💡 Carla-Tipp des Tages / Carla's Tip of the Day")
    st.warning(adventure.carla_tip)

    st.markdown("### ⚠ Sicherheit / Safety")
    for risk in adventure.safety.risks:
        st.markdown(f"- **Risiko / Risk:** {risk}")

    st.markdown("**Prävention / Prevention:**")
    for prevention_item in adventure.safety.prevention:
        st.markdown(f"- {prevention_item}")

    st.markdown("### 🩹 Mini-Reiseapotheke / Mini Travel First-Aid Kit")
    for item in DEFAULT_REISEAPOTHEKE:
        st.markdown(f"- {item}")

    st.markdown("### 🔗 Google Integrationen / Google Integrations")
    if not user_key:
        st.info(
            "Bitte zuerst eine User-ID oder E-Mail eingeben und Google verbinden. / "
            "Please enter a user ID or email and connect Google first."
        )
        return

    calendar_col, mail_col = st.columns(2)
    with calendar_col:
        if st.button(
            "📅 In Kalender eintragen / Add to Calendar", use_container_width=True
        ):
            start_time = datetime.now().replace(second=0, microsecond=0)
            try:
                create_event(
                    user_key=user_key,
                    event_input=CalendarEventInput(
                        title=adventure.title,
                        description=adventure.description,
                        start_time=start_time,
                    ),
                )
            except OAuthConfigurationError as error:
                st.error(f"Google OAuth fehlt / Google OAuth is missing: {error}")
            else:
                st.success("Event erstellt! / Event created!")

    with mail_col:
        if st.button("📧 Per Mail senden / Send by Email", use_container_width=True):
            now = datetime.now().replace(second=0, microsecond=0)
            html_content = build_daily_scheduler_email_html(
                DailyDigestInput(
                    recipient_email=user_key,
                    adventure_title=adventure.title,
                    adventure_description=adventure.description,
                    weather_summary="Partly cloudy in Düsseldorf",
                    scheduled_for=now.replace(hour=8, minute=20),
                )
            )
            ics_bytes = build_ics_attachment(
                title=adventure.title,
                description=adventure.description,
                start_time=now,
                end_time=now + timedelta(hours=1),
                location=adventure.location,
            )
            try:
                send_html_email(
                    user_key=user_key,
                    to=user_key,
                    subject=f"Mikroabenteuer: {adventure.title}",
                    html_content=html_content,
                    from_email=sender_email,
                    ics_attachment=ics_bytes,
                )
            except OAuthConfigurationError as error:
                st.error(f"Google OAuth fehlt / Google OAuth is missing: {error}")
            else:
                st.success("Mail versendet! / Email sent!")
