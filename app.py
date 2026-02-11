import base64
import os
from datetime import date
from pathlib import Path

import streamlit as st

from mikroabenteuer.config import APP_TITLE
from mikroabenteuer.data_loader import load_adventures
from mikroabenteuer.openai_settings import configure_openai_api_key
from mikroabenteuer.scheduler import start_scheduler
from mikroabenteuer.ui.details import render_adventure_details
from mikroabenteuer.ui.table import render_adventure_table

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌿",
    layout="wide",
)


def inject_custom_styles(background_path: Path) -> None:
    """Inject a light, readable theme with a custom background image."""
    background_b64 = base64.b64encode(background_path.read_bytes()).decode("utf-8")

    st.markdown(
        f"""
        <style>
            .stApp {{
                background: linear-gradient(
                    rgba(255, 255, 255, 0.87),
                    rgba(255, 255, 255, 0.87)
                ), url("data:image/png;base64,{background_b64}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
                color: #1f2937;
            }}

            h1, h2, h3, .stCaption, p, label, span {{
                color: #1f2937 !important;
            }}

            [data-testid="stMetric"],
            [data-testid="stExpander"],
            [data-testid="stDataFrame"],
            [data-testid="stMarkdownContainer"] > div,
            .stTextInput > div > div,
            .stSelectbox > div > div {{
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 0.8rem;
            }}

            .stButton > button {{
                background-color: #2563eb;
                color: #ffffff;
                border: none;
            }}

            .stButton > button:hover {{
                background-color: #1d4ed8;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_custom_styles(Path("Hintergrund.png"))

top_col_left, top_col_center, top_col_right = st.columns([1, 1.6, 1])
with top_col_center:
    st.image(
        image="20251219_155329.jpg",
        width=240,
    )

configure_openai_api_key()

if os.getenv("ENABLE_DAILY_SCHEDULER", "0") == "1":
    try:
        start_scheduler()
    except Exception:
        st.warning(
            "Scheduler konnte nicht gestartet werden / Scheduler could not be started.",
        )

adventures = load_adventures()

today = date.today().isoformat()
todays_adventure = adventures[hash(today) % len(adventures)]

st.divider()
st.header("📅 Abenteuer des Tages")
render_adventure_details(todays_adventure, expanded=True)

st.divider()
st.header("🗺 Alle Mikroabenteuer")
render_adventure_table(adventures)
