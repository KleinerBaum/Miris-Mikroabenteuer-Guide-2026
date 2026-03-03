from __future__ import annotations

from typing import cast

import streamlit as st
from pydantic import ValidationError

from mikroabenteuer.config import AppConfig
from mikroabenteuer.constants import Language
from mikroabenteuer.data_seed import seed_adventures
from mikroabenteuer.materials import MATERIAL_LABELS
from mikroabenteuer.models import (
    ActivitySearchCriteria,
    MicroAdventure,
)
from mikroabenteuer.recommender import filter_adventures
from mikroabenteuer.settings import load_runtime_config, render_missing_config_ui


def _t(lang: Language, de: str, en: str) -> str:
    _ = (lang, en)
    return de


def _material_label(material_key: str) -> str:
    return MATERIAL_LABELS.get(material_key, material_key)


def _load_adventures() -> list[MicroAdventure]:
    return seed_adventures()


def _get_criteria(cfg: AppConfig) -> ActivitySearchCriteria:
    if "criteria_daily" not in st.session_state:
        raise RuntimeError(
            "Bitte zuerst die Hauptseite nutzen, damit Suchkriterien vorliegen."
        )
    return cast(ActivitySearchCriteria, st.session_state["criteria_daily"])


def _render_preview_list(title: str, items: list[str]) -> None:
    if not items:
        return
    preview = items[:3]
    st.markdown(f"**{title}**")
    for item in preview:
        st.markdown(f"- {item}")
    if len(items) > 3:
        with st.expander("Mehr…", expanded=False):
            for item in items[3:]:
                st.markdown(f"- {item}")


def _render_adventure_card(adventure: MicroAdventure, lang: Language) -> None:
    with st.container(border=True):
        st.markdown(
            f"### {adventure.title} · {adventure.area} · {adventure.duration_minutes} min"
        )
        st.write(adventure.short)
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(
            f"- **{_t(lang, 'Dauer', '')}:** {adventure.duration_minutes} min"
        )
        col2.markdown(
            f"- **{_t(lang, 'Distanz', '')}:** {adventure.distance_km:.1f} km"
        )
        col3.markdown(f"- **{_t(lang, 'Sicherheit', '')}:** {adventure.safety_level}")
        col4.markdown(
            f"- **{_t(lang, 'Altersgruppe', '')}:** {adventure.age_min}-{adventure.age_max}"
        )
        st.markdown(
            f"- **{_t(lang, 'Kinderwagen', '')}:** {'Ja' if adventure.stroller_ok else 'Nein'}"
        )

        _render_preview_list(_t(lang, "Ablauf", ""), adventure.route_steps)
        _render_preview_list(_t(lang, "Tipps", ""), adventure.execution_tips)
        _render_preview_list(_t(lang, "Varianten", ""), adventure.variations)


def main() -> None:
    try:
        cfg = load_runtime_config()
    except ValidationError as error:
        render_missing_config_ui(error)
        return

    lang: Language = cast(Language, st.session_state.get("lang", "DE"))
    st.title("Bibliothek")

    try:
        criteria = _get_criteria(cfg)
    except RuntimeError as exc:
        st.info(str(exc))
        return

    adventures = _load_adventures()
    filtered = filter_adventures(adventures, criteria)

    st.caption(
        _t(lang, f"{len(filtered)} passende Abenteuer (von {len(adventures)}).", "")
    )
    if not filtered:
        st.info(
            _t(lang, "Keine Treffer. Bitte Filter auf der Hauptseite anpassen.", "")
        )
        return

    for adventure in filtered:
        _render_adventure_card(adventure, lang)


if __name__ == "__main__":
    main()
