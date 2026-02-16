from __future__ import annotations

import streamlit as st

from ..models import Adventure
from .details import render_adventure_details


def render_adventure_table(adventures: list[Adventure]) -> None:
    for index, adventure in enumerate(adventures):
        with st.expander(f"🌱 {adventure.title}"):
            render_adventure_details(adventure, key_prefix=f"table-{index}")
