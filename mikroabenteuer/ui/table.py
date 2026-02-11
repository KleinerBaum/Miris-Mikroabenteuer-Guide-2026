from typing import List

import streamlit as st

from ..models import Adventure
from .details import render_adventure_details


def render_adventure_table(adventures: List[Adventure]) -> None:
    for adventure in adventures:
        with st.expander(f"🌱 {adventure.title}"):
            render_adventure_details(adventure)
