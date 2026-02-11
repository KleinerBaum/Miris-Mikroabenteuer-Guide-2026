from __future__ import annotations

import secrets
from datetime import date

import streamlit as st

from mikroabenteuer.config import APP_TITLE
from mikroabenteuer.data_loader import load_adventures
from mikroabenteuer.google.auth import (
    OAuthConfigurationError,
    build_authorization_url,
    exchange_code_and_store_token,
)
from mikroabenteuer.openai_settings import configure_openai_api_key
from mikroabenteuer.ui.details import render_adventure_details
from mikroabenteuer.ui.table import render_adventure_table

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 Mikroabenteuer mit Carla / Micro Adventures with Carla")
st.caption("Kleine Abenteuer. Große Erinnerungen. / Small adventures. Big memories.")

configure_openai_api_key()

sender_email = st.text_input(
    "Sender E-Mail (Google) / Sender email (Google)",
    value="gerrit.fabisch2024@gmail.com",
)
user_key = st.text_input(
    "User-ID oder E-Mail / User ID or email",
    value="",
    help=(
        "Wird als Key für per-User OAuth Token genutzt. / "
        "Used as key for per-user OAuth token storage."
    ),
)

query_params = st.query_params
if "oauth_state" not in st.session_state:
    st.session_state.oauth_state = ""
if "oauth_url" not in st.session_state:
    st.session_state.oauth_url = ""

if query_params.get("code") and query_params.get("state"):
    oauth_code = str(query_params["code"])
    oauth_state = str(query_params["state"])
    if oauth_state != st.session_state.oauth_state:
        st.error("Ungültiger OAuth State / Invalid OAuth state")
    elif not user_key:
        st.error("User-Key fehlt / Missing user key")
    else:
        try:
            exchange_code_and_store_token(user_key=user_key, code=oauth_code)
        except OAuthConfigurationError as error:
            st.error(
                f"OAuth Konfiguration fehlt / OAuth configuration missing: {error}"
            )
        else:
            st.success("Google Konto verbunden! / Google account connected!")
    st.query_params.clear()

connect_col, status_col = st.columns([1, 2])
with connect_col:
    if st.button(
        "Google Konto verbinden / Connect Google account", disabled=not bool(user_key)
    ):
        state = secrets.token_urlsafe(32)
        st.session_state.oauth_state = state
        try:
            auth_url = build_authorization_url(user_key=user_key, state=state)
        except OAuthConfigurationError as error:
            st.error(
                f"OAuth Konfiguration fehlt / OAuth configuration missing: {error}"
            )
        else:
            st.session_state.oauth_url = auth_url

if st.session_state.oauth_url:
    st.link_button(
        "OAuth öffnen / Open OAuth",
        st.session_state.oauth_url,
        use_container_width=True,
    )

with status_col:
    st.caption(
        "Redirect URI muss exakt gesetzt sein: https://mikrocarla.streamlit.app/ / "
        "Redirect URI must exactly match: https://mikrocarla.streamlit.app/"
    )

adventures = load_adventures()

today = date.today().isoformat()
todays_adventure = adventures[hash(today) % len(adventures)]

st.divider()
st.header("📅 Abenteuer des Tages / Adventure of the Day")
render_adventure_details(
    todays_adventure,
    user_key=user_key if user_key else None,
    sender_email=sender_email,
    expanded=True,
)

st.divider()
st.header("🗺 Alle Mikroabenteuer / All Micro Adventures")
render_adventure_table(
    adventures,
    user_key=user_key if user_key else None,
    sender_email=sender_email,
)
