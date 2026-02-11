from typing import List

import pandas as pd
import streamlit as st

from ..models import Adventure
from .details import render_adventure_details


def render_adventure_table(adventures: List[Adventure]) -> None:
    df = pd.DataFrame(
        [
            {
                "Titel": adventure.title,
                "Ort": adventure.location,
                "Dauer": adventure.duration,
            }
            for adventure in adventures
        ]
    )

    st.data_editor(
        df,
        width="stretch",
        hide_index=True,
        key="adventure_table",
        disabled=True,
    )

    for adventure in adventures:
        with st.expander(f"🌱 {adventure.title}"):
            render_adventure_details(adventure)
