from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import streamlit as st
from pydantic import ValidationError

from mikroabenteuer.config import AppConfig
from mikroabenteuer.constants import (
    EFFORT_LEVELS,
    Language,
    effort_label,
    theme_label,
    theme_options,
)
from mikroabenteuer.data_seed import seed_adventures
from mikroabenteuer.materials import (
    COMMON_HOUSEHOLD_MATERIALS,
    MATERIAL_ALIASES,
    MATERIAL_LABELS,
)
from mikroabenteuer.models import DevelopmentDomain, MicroAdventure
from mikroabenteuer.settings import load_runtime_config, render_missing_config_ui

DOMAIN_LABELS: dict[DevelopmentDomain, str] = {
    DevelopmentDomain.gross_motor: "Grobmotorik",
    DevelopmentDomain.fine_motor: "Feinmotorik",
    DevelopmentDomain.language: "Sprache",
    DevelopmentDomain.social_emotional: "Sozial-emotional",
    DevelopmentDomain.sensory: "Sensorik",
    DevelopmentDomain.cognitive: "Kognitiv",
}

GOAL_OPTIONS: tuple[DevelopmentDomain, ...] = (
    DevelopmentDomain.gross_motor,
    DevelopmentDomain.fine_motor,
    DevelopmentDomain.language,
    DevelopmentDomain.social_emotional,
    DevelopmentDomain.sensory,
    DevelopmentDomain.cognitive,
)


@dataclass(frozen=True)
class LibraryFilters:
    query: str
    effort_levels: list[str]
    age_range: tuple[float, float]
    duration_range: tuple[int, int]
    max_distance_km: float
    stroller_mode: str
    topics: list[str]
    goals: list[DevelopmentDomain]
    available_materials: list[str]


def _t(lang: Language, de: str, en: str) -> str:
    return de if lang == "DE" else en


def _material_label(material_key: str) -> str:
    return MATERIAL_LABELS.get(material_key, material_key)


def _load_adventures() -> list[MicroAdventure]:
    return seed_adventures()


def _render_preview_list(title: str, items: list[str], *, lang: Language) -> None:
    if not items:
        return
    preview = items[:3]
    st.markdown(f"**{title}**")
    for item in preview:
        st.markdown(f"- {item}")
    if len(items) > 3:
        with st.expander(_t(lang, "Mehr… / More…", "More… / Mehr…"), expanded=False):
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
            f"- **{_t(lang, 'Dauer / Duration', 'Duration / Dauer')}:** {adventure.duration_minutes} min"
        )
        col2.markdown(
            f"- **{_t(lang, 'Distanz / Distance', 'Distance / Distanz')}:** {adventure.distance_km:.1f} km"
        )
        col3.markdown(
            f"- **{_t(lang, 'Sicherheit / Safety', 'Safety / Sicherheit')}:** {adventure.safety_level}"
        )
        col4.markdown(
            f"- **{_t(lang, 'Altersgruppe / Age range', 'Age range / Altersgruppe')}:** {adventure.age_min}-{adventure.age_max}"
        )
        stroller_label = (
            _t(lang, "Ja / Yes", "Yes / Ja")
            if adventure.stroller_ok
            else _t(lang, "Nein / No", "No / Nein")
        )
        st.markdown(
            f"- **{_t(lang, 'Kinderwagen / Stroller', 'Stroller / Kinderwagen')}:** {stroller_label}"
        )

        _render_preview_list(
            _t(lang, "Ablauf / Steps", "Steps / Ablauf"),
            adventure.route_steps,
            lang=lang,
        )
        _render_preview_list(
            _t(lang, "Tipps / Tips", "Tips / Tipps"),
            adventure.execution_tips,
            lang=lang,
        )
        _render_preview_list(
            _t(lang, "Varianten / Variants", "Variants / Varianten"),
            adventure.variations,
            lang=lang,
        )


def _render_library_filters(
    adventures: list[MicroAdventure], lang: Language
) -> LibraryFilters:
    st.markdown(
        f"**{_t(lang, 'Filter & Suche / Filters & Search', 'Filters & Search / Filter & Suche')}**"
    )
    min_age = min(adventure.age_min for adventure in adventures)
    max_age = max(adventure.age_max for adventure in adventures)
    min_duration = min(adventure.duration_minutes for adventure in adventures)
    max_duration = max(adventure.duration_minutes for adventure in adventures)
    max_distance = max(adventure.distance_km for adventure in adventures)

    col_left, col_mid, col_right = st.columns(3)

    with col_left:
        st.markdown(
            f"**{_t(lang, 'Suche & Aufwand / Search & Effort', 'Search & Effort / Suche & Aufwand')}**"
        )
        query = st.text_input(
            _t(lang, "Freitextsuche / Text search", "Text search / Freitextsuche"),
            value="",
            placeholder=_t(
                lang,
                "Titel, Gebiet, Tags oder Kurzbeschreibung… / Title, area, tags or summary…",
                "Title, area, tags or summary… / Titel, Gebiet, Tags oder Kurzbeschreibung…",
            ),
        ).strip()
        effort_levels = st.multiselect(
            _t(lang, "Aufwand / Effort", "Effort / Aufwand"),
            options=list(EFFORT_LEVELS),
            default=[],
            format_func=lambda value: effort_label(value, lang),
        )
        stroller_mode = st.selectbox(
            _t(lang, "Kinderwagen / Stroller", "Stroller / Kinderwagen"),
            options=["all", "yes", "no"],
            index=0,
            format_func=lambda value: {
                "all": _t(lang, "Alle / All", "All / Alle"),
                "yes": _t(
                    lang, "Nur geeignet / Suitable only", "Suitable only / Nur geeignet"
                ),
                "no": _t(
                    lang,
                    "Nur nicht geeignet / Not suitable only",
                    "Not suitable only / Nur nicht geeignet",
                ),
            }[value],
        )

    with col_mid:
        st.markdown(f"**{_t(lang, 'Rahmen / Conditions', 'Conditions / Rahmen')}**")
        age_range = st.slider(
            _t(lang, "Alter (Jahre) / Age (years)", "Age (years) / Alter (Jahre)"),
            min_value=float(min_age),
            max_value=float(max_age),
            value=(float(min_age), float(max_age)),
            step=0.5,
        )
        duration_range = st.slider(
            _t(
                lang,
                "Dauer (Minuten) / Duration (minutes)",
                "Duration (minutes) / Dauer (Minuten)",
            ),
            min_value=int(min_duration),
            max_value=int(max_duration),
            value=(int(min_duration), int(max_duration)),
            step=5,
        )
        max_distance_km = st.slider(
            _t(
                lang,
                "Max. Distanz (km) / Max distance (km)",
                "Max distance (km) / Max. Distanz (km)",
            ),
            min_value=0.0,
            max_value=float(max_distance),
            value=float(max_distance),
            step=0.5,
        )

    with col_right:
        st.markdown(f"**{_t(lang, 'Inhalte / Content', 'Content / Inhalte')}**")
        topics = st.multiselect(
            _t(lang, "Themen / Topics", "Topics / Themen"),
            options=theme_options(lang),
            default=[],
            format_func=lambda value: theme_label(value, lang),
        )
        goals = st.multiselect(
            _t(lang, "Ziele / Goals", "Goals / Ziele"),
            options=list(GOAL_OPTIONS),
            default=[],
            format_func=lambda goal: DOMAIN_LABELS[cast(DevelopmentDomain, goal)],
        )
        available_materials = st.multiselect(
            _t(lang, "Materialien / Materials", "Materials / Materialien"),
            options=list(COMMON_HOUSEHOLD_MATERIALS),
            default=[],
            format_func=_material_label,
        )

    return LibraryFilters(
        query=query,
        effort_levels=effort_levels,
        age_range=age_range,
        duration_range=duration_range,
        max_distance_km=max_distance_km,
        stroller_mode=stroller_mode,
        topics=topics,
        goals=goals,
        available_materials=available_materials,
    )


def _matches_query(adventure: MicroAdventure, query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        [
            adventure.title,
            adventure.area,
            adventure.short,
            *adventure.tags,
            *adventure.mood_tags,
            *adventure.weather_tags,
        ]
    ).lower()
    return query.lower() in haystack


def _matches_filters(adventure: MicroAdventure, filters: LibraryFilters) -> bool:
    if filters.effort_levels and adventure.energy_level not in filters.effort_levels:
        return False
    if (
        adventure.age_max < filters.age_range[0]
        or adventure.age_min > filters.age_range[1]
    ):
        return False
    if not (
        filters.duration_range[0]
        <= adventure.duration_minutes
        <= filters.duration_range[1]
    ):
        return False
    if adventure.distance_km > filters.max_distance_km:
        return False
    if filters.stroller_mode == "yes" and not adventure.stroller_ok:
        return False
    if filters.stroller_mode == "no" and adventure.stroller_ok:
        return False
    if filters.topics:
        adventure_signals = (
            set(adventure.tags)
            | set(adventure.mood_tags)
            | set(adventure.weather_tags)
            | set(adventure.season_tags)
        )
        topic_match_map: dict[str, set[str]] = {
            "nature": {"Natur"},
            "movement": {"Bewegung", "Motorik", "Abenteuer"},
            "creative": {"Kreativ", "Musik", "Sprache"},
            "learning": {"Lernen"},
            "mindfulness": {"Achtsamkeit", "Ruhig"},
            "social": {"Sozial", "Werte", "Bonding", "Alltag"},
            "water": {"Wasser"},
            "rain": {"Regen"},
            "wind": {"Wind"},
            "winter": {"Winter"},
            "evening": {"Abend"},
            "playground": {"Spielplatz"},
        }
        if not any(
            any(
                signal in adventure_signals
                for signal in topic_match_map.get(topic, {topic})
            )
            for topic in filters.topics
        ):
            return False
    if filters.goals:
        goal_signal_map: dict[DevelopmentDomain, set[str]] = {
            DevelopmentDomain.gross_motor: {
                "Grobmotorik",
                "Bewegung",
                "Koordination",
                "Körpergefühl",
            },
            DevelopmentDomain.fine_motor: {
                "Feinmotorik",
                "Hand-Auge",
                "Greifen",
                "Sortieren",
            },
            DevelopmentDomain.language: {
                "Sprache",
                "Wortschatz",
                "Erzählen",
                "Hypothesen",
            },
            DevelopmentDomain.social_emotional: {
                "Empathie",
                "Teamwork",
                "Sozial",
                "Respekt",
                "Bindung",
            },
            DevelopmentDomain.sensory: {"Sensorik", "Achtsamkeit", "Wahrnehmung"},
            DevelopmentDomain.cognitive: {
                "Kategorisieren",
                "Gedächtnis",
                "Vergleich",
                "Ursache/Wirkung",
            },
        }
        benefit_signals = set(adventure.toddler_benefits) | set(adventure.tags)
        if not any(
            any(
                signal in benefit_signals
                for signal in goal_signal_map.get(goal, {goal.value})
            )
            for goal in filters.goals
        ):
            return False
    if filters.available_materials:
        haystack = " ".join(adventure.packing_list + adventure.preparation).lower()
        if not all(
            any(
                alias in haystack
                for alias in MATERIAL_ALIASES.get(material, (material,))
            )
            for material in filters.available_materials
        ):
            return False
    if not _matches_query(adventure, filters.query):
        return False
    return True


def _filter_adventures(
    adventures: list[MicroAdventure], filters: LibraryFilters
) -> list[MicroAdventure]:
    return [
        adventure for adventure in adventures if _matches_filters(adventure, filters)
    ]


def _sort_adventures(adventures: list[MicroAdventure]) -> list[MicroAdventure]:
    return sorted(
        adventures,
        key=lambda adventure: (
            adventure.title.lower(),
            adventure.duration_minutes,
            adventure.distance_km,
        ),
    )


def main() -> None:
    try:
        _cfg: AppConfig = load_runtime_config()
    except ValidationError as error:
        render_missing_config_ui(error)
        return

    lang: Language = cast(Language, st.session_state.get("lang", "DE"))
    st.title("Bibliothek")

    adventures = _load_adventures()
    filters = _render_library_filters(adventures, lang)
    filtered = _sort_adventures(_filter_adventures(adventures, filters))

    st.caption(
        _t(
            lang,
            f"{len(filtered)} passende Abenteuer (von {len(adventures)}). / {len(filtered)} matching adventures (of {len(adventures)}).",
            f"{len(filtered)} matching adventures (of {len(adventures)}). / {len(filtered)} passende Abenteuer (von {len(adventures)}).",
        )
    )
    if not filtered:
        st.info(
            _t(
                lang,
                "Keine Treffer. Bitte Filter oder Suche anpassen. / No matches. Please adjust filters or search.",
                "No matches. Please adjust filters or search. / Keine Treffer. Bitte Filter oder Suche anpassen.",
            )
        )
        return

    for adventure in filtered:
        _render_adventure_card(adventure, lang)


if __name__ == "__main__":
    main()
