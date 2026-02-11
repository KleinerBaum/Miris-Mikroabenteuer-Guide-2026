from datetime import date

import streamlit as st

from mikroabenteuer.config import APP_TITLE
from mikroabenteuer.data_loader import load_adventures
from mikroabenteuer.openai_settings import configure_openai_api_key
from mikroabenteuer.ui.details import render_adventure_details
from mikroabenteuer.ui.table import render_adventure_table

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 Mikroabenteuer mit Carla")
st.caption("Kleine Abenteuer. Große Erinnerungen.")

configure_openai_api_key()


adventures = load_adventures()

today = date.today().isoformat()
todays_adventure = adventures[hash(today) % len(adventures)]

st.divider()
st.header("📅 Abenteuer des Tages")
render_adventure_details(todays_adventure, expanded=True)

st.divider()
st.header("🗺 Alle Mikroabenteuer")
render_adventure_table(adventures)
