# ruff: noqa: E402
from __future__ import annotations

import base64
import json
import os
import sys
import time as time_module
from datetime import date, datetime, time, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional, cast

import re

import streamlit as st
import streamlit.components.v1 as components
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mikroabenteuer.config import AppConfig
from src.mikroabenteuer.constants import (
    Language,
    effort_label,
    theme_label,
    theme_options,
)
from src.mikroabenteuer.data_seed import seed_adventures
from src.mikroabenteuer.email_templates import render_daily_email_html
from src.mikroabenteuer.activity_library import suggest_activities_offline
from src.mikroabenteuer.ics import build_ics_event
from src.mikroabenteuer.materials import (
    COMMON_HOUSEHOLD_MATERIALS,
    MATERIAL_LABELS,
)
from src.mikroabenteuer.models import (
    ActivitySearchCriteria,
    DevelopmentDomain,
    TimeWindow,
    WeatherCondition as EventWeatherCondition,
    WeatherSummary as EventWeatherSummary,
    ActivityPlan,
    MicroAdventure,
)
from src.mikroabenteuer.openai_gen import (
    ActivityGenerationError,
    generate_activity_plan,
    render_activity_plan_markdown,
)
from src.mikroabenteuer.plan_reports import (
    REPORT_REASONS,
    load_plan_reports,
    save_plan_report,
)
from src.mikroabenteuer.recommender import filter_adventures, pick_daily_adventure
from src.mikroabenteuer.scheduler import run_daily_job_once
from src.mikroabenteuer.settings import load_runtime_config, render_missing_config_ui
from src.mikroabenteuer.weather import WeatherSummary, fetch_weather_for_day


st.set_page_config(page_title="Mikroabenteuer", page_icon="🌿", layout="wide")


@dataclass(frozen=True)
class FamilyProfile:
    child_name: str
    parent_names: str
    child_age_years: float


AGE_BAND_OPTIONS: tuple[tuple[str, float], ...] = (
    ("2-3", 2.5),
    ("4-5", 4.5),
    ("6-8", 7.0),
    ("9-12", 10.5),
)

DURATION_OPTIONS: tuple[int, ...] = (30, 45, 60, 90, 120, 180, 240, 300, 360)
GOAL_OPTIONS: tuple[DevelopmentDomain, ...] = (
    DevelopmentDomain.gross_motor,
    DevelopmentDomain.fine_motor,
    DevelopmentDomain.language,
    DevelopmentDomain.social_emotional,
    DevelopmentDomain.sensory,
    DevelopmentDomain.cognitive,
)

DOMAIN_LABELS: dict[DevelopmentDomain, str] = {
    DevelopmentDomain.gross_motor: "Grobmotorik / Gross motor",
    DevelopmentDomain.fine_motor: "Feinmotorik / Fine motor",
    DevelopmentDomain.language: "Sprache / Language",
    DevelopmentDomain.social_emotional: "Sozial-emotional / Social-emotional",
    DevelopmentDomain.sensory: "Sensorik / Sensory",
    DevelopmentDomain.cognitive: "Kognitiv / Cognitive",
}
CONSTRAINT_OPTIONS: tuple[str, ...] = (
    "Kein Auto / No car",
    "Kinderwagen / Stroller",
    "Wetterfest / Weather-proof",
    "Niedriges Budget / Low budget",
    "Reizarm / Low sensory",
    "Barrierearm / Accessible",
)

MATERIAL_OPTIONS: tuple[str, ...] = COMMON_HOUSEHOLD_MATERIALS


def _material_label(material_key: str) -> str:
    return MATERIAL_LABELS.get(material_key, material_key)


def _sanitize_optional_text(value: str, *, max_chars: int = 80) -> str:
    cleaned = re.sub(r"[^\w\s,\-äöüÄÖÜß]", "", (value or "").strip())
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_chars].rstrip()


def _optional_csv_items(value: str, *, max_items: int = 2) -> list[str]:
    normalized = _sanitize_optional_text(value)
    if not normalized:
        return []
    return [part.strip() for part in normalized.split(",") if part.strip()][:max_items]


def _replace_family_tokens(text: str, profile: FamilyProfile) -> str:
    sanitized = text.replace("Carla", profile.child_name)
    sanitized = sanitized.replace("Miriam", profile.parent_names)
    sanitized = sanitized.replace("Miri", profile.parent_names)
    return sanitized.replace("2,5", f"{profile.child_age_years:.1f}".replace(".", ","))


def _profiled_adventure(
    adventure: MicroAdventure, profile: FamilyProfile
) -> MicroAdventure:
    return MicroAdventure(
        slug=adventure.slug,
        title=_replace_family_tokens(adventure.title, profile),
        area=adventure.area,
        short=_replace_family_tokens(adventure.short, profile),
        duration_minutes=adventure.duration_minutes,
        distance_km=adventure.distance_km,
        best_time=adventure.best_time,
        stroller_ok=adventure.stroller_ok,
        start_point=_replace_family_tokens(adventure.start_point, profile),
        route_steps=[
            _replace_family_tokens(step, profile) for step in adventure.route_steps
        ],
        preparation=[
            _replace_family_tokens(item, profile) for item in adventure.preparation
        ],
        packing_list=[
            _replace_family_tokens(item, profile) for item in adventure.packing_list
        ],
        execution_tips=[
            _replace_family_tokens(item, profile) for item in adventure.execution_tips
        ],
        variations=[
            _replace_family_tokens(item, profile) for item in adventure.variations
        ],
        toddler_benefits=[
            _replace_family_tokens(item, profile) for item in adventure.toddler_benefits
        ],
        carla_tip=_replace_family_tokens(adventure.carla_tip, profile),
        risks=[_replace_family_tokens(item, profile) for item in adventure.risks],
        mitigations=[
            _replace_family_tokens(item, profile) for item in adventure.mitigations
        ],
        tags=list(adventure.tags),
        accessibility=list(adventure.accessibility),
        season_tags=list(adventure.season_tags),
        weather_tags=list(adventure.weather_tags),
        energy_level=adventure.energy_level,
        difficulty=adventure.difficulty,
        age_min=adventure.age_min,
        age_max=adventure.age_max,
        mood_tags=list(adventure.mood_tags),
        safety_level=adventure.safety_level,
    )


def _t(lang: Language, de: str, en: str) -> str:
    _ = (lang, en)
    return de


def _truncate_text_with_limit(text: str, *, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _consume_request_budget(cfg: AppConfig, *, lang: Language, scope: str) -> bool:
    count = int(st.session_state.get("request_count", 0))
    if count >= cfg.max_requests_per_session:
        st.warning(
            _t(
                lang,
                f"Session-Limit erreicht ({cfg.max_requests_per_session} Anfragen). Bitte Seite neu laden. / Session limit reached ({cfg.max_requests_per_session} requests). Please reload the page.",
                "",
            )
        )
        return False

    st.session_state["request_count"] = count + 1
    current = int(st.session_state["request_count"])
    st.caption(
        _t(
            lang,
            f"Anfragebudget {current}/{cfg.max_requests_per_session} ({scope}). / Request budget {current}/{cfg.max_requests_per_session} ({scope}).",
            "",
        )
    )
    return True


def inject_custom_styles(background_path: Path) -> None:
    if not background_path.exists():
        return

    background_b64 = base64.b64encode(background_path.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <style>
            :root {{
                --primary-dark-green: #00715D;
                --primary-mint: #A4D4AE;
                --accent-terracotta: #D98556;
                --accent-marigold: #F4B400;
                --secondary-sky-blue: #80C7CF;
                --secondary-lavender: #B8B1D3;
                --background-cream: #F9F4E7;
                --text-charcoal: #2F353D;
                --line-soft: #E3E6E9;
            }}
            .stApp {{
                background: linear-gradient(
                    rgba(249, 244, 231, 0.92),
                    rgba(249, 244, 231, 0.92)
                ), url("data:image/png;base64,{background_b64}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
                color: var(--text-charcoal);
            }}
            h1, h2, h3, .stCaption, p, label {{ color: var(--text-charcoal) !important; }}
            .stDownloadButton button,
            .stButton button {{
                background-color: var(--primary-dark-green) !important;
                color: #ffffff !important;
                border: 1px solid #00584a !important;
            }}
            .stDownloadButton button:hover,
            .stButton button:hover {{
                background-color: var(--primary-mint) !important;
                color: var(--text-charcoal) !important;
                border-color: #7fbb8f !important;
            }}
            .stDownloadButton button:disabled {{
                background-color: var(--line-soft) !important;
                color: #515862 !important;
                border-color: #c7cfd4 !important;
            }}
            [data-testid="stSidebar"] {{
                background-color: rgba(128, 199, 207, 0.22) !important;
                border-right: 1px solid var(--line-soft);
            }}
            [data-testid="stExpander"] {{
                border: 1px solid var(--line-soft) !important;
                border-radius: 0.75rem !important;
                background-color: rgba(184, 177, 211, 0.2);
            }}
            .stExpander summary {{
                background-color: var(--primary-dark-green) !important;
                border-radius: 0.75rem !important;
            }}
            .stExpander [data-testid="stExpanderToggleIcon"],
            .stExpander summary p,
            .stExpander summary span {{
                color: #ffffff !important;
            }}
            .stExpander div[data-testid="stExpanderDetails"] pre,
            .stExpander div[data-testid="stExpanderDetails"] code,
            .stExpander div[data-testid="stExpanderDetails"] span {{
                color: var(--text-charcoal) !important;
            }}
            .stMetric,
            [data-testid="stMetricValue"],
            [data-testid="stMetricLabel"] {{
                color: var(--text-charcoal) !important;
            }}
            .stAlert {{
                border: 1px solid var(--line-soft) !important;
                background-color: rgba(164, 212, 174, 0.2) !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _load_adventures() -> list[MicroAdventure]:
    return seed_adventures()


@st.cache_data(show_spinner=False)
def _get_weather(day_iso: str, tz: str) -> WeatherSummary:
    y, m, d = map(int, day_iso.split("-"))
    return fetch_weather_for_day(date(y, m, d), timezone=tz)


CRITERIA_DAILY_KEY = "criteria_daily"
CRITERIA_EVENTS_KEY = "criteria_events"


def _default_criteria(cfg: AppConfig) -> ActivitySearchCriteria:
    default_date = date.today()
    default_start = time(hour=9, minute=0)
    default_effort = (
        cfg.default_effort
        if cfg.default_effort in {"niedrig", "mittel", "hoch"}
        else "mittel"
    )
    return ActivitySearchCriteria(
        plz=cfg.default_postal_code,
        radius_km=cfg.default_radius_km,
        date=default_date,
        time_window=TimeWindow(
            start=default_start,
            end=(
                datetime.combine(default_date, default_start)
                + timedelta(minutes=int(cfg.default_available_minutes))
            ).time(),
        ),
        effort=cast(Literal["niedrig", "mittel", "hoch"], default_effort),
        budget_eur_max=cfg.default_budget_eur,
        topics=[],
    )


def get_criteria_state(
    cfg: AppConfig, *, key: str = CRITERIA_DAILY_KEY
) -> ActivitySearchCriteria:
    # Zentrale Quelle für die Filterlogik.
    # Nur diese Funktion setzt Initialwerte; UI-Adapter lesen/schreiben lediglich dieses Objekt.
    if key not in st.session_state:
        st.session_state[key] = _default_criteria(cfg)
    return cast(ActivitySearchCriteria, st.session_state[key])


CRITERIA_WIDGET_FIELDS: tuple[str, ...] = (
    "plz",
    "radius_km",
    "date",
    "start_time",
    "available_minutes",
    "effort",
    "budget_eur_max",
    "topics",
    "location_preference",
    "goals",
    "constraints",
    "available_materials",
)


def _criteria_to_widget_values(criteria: ActivitySearchCriteria) -> dict[str, Any]:
    available_minutes = max(
        15,
        int(
            (
                datetime.combine(criteria.date, criteria.end_time)
                - datetime.combine(criteria.date, criteria.start_time)
            ).total_seconds()
            // 60
        ),
    )
    return {
        "plz": criteria.plz,
        "radius_km": float(criteria.radius_km),
        "date": criteria.date,
        "start_time": criteria.start_time,
        "available_minutes": available_minutes,
        "effort": criteria.effort,
        "budget_eur_max": float(criteria.budget_eur_max),
        "topics": list(criteria.topics),
        "location_preference": criteria.location_preference,
        "goals": list(criteria.goals),
        "constraints": list(criteria.constraints),
        "available_materials": list(criteria.available_materials),
    }


def _ensure_ui_adapter_state(prefix: str, criteria: ActivitySearchCriteria) -> None:
    widget_values = _criteria_to_widget_values(criteria)
    for field in CRITERIA_WIDGET_FIELDS:
        key = f"{prefix}_{field}"
        if key not in st.session_state:
            st.session_state[key] = widget_values[field]


def _sync_widget_change_to_criteria(
    prefix: str,
    *,
    state_key: str,
    raise_on_error: bool = False,
) -> None:
    try:
        st.session_state[state_key] = _build_criteria_from_widget_state(prefix=prefix)
    except ValidationError:
        if raise_on_error:
            raise
        return


def _build_criteria_from_widget_state(*, prefix: str) -> ActivitySearchCriteria:
    target_date = cast(date, st.session_state[f"{prefix}_date"])
    start_time = cast(time, st.session_state[f"{prefix}_start_time"])
    available_minutes = int(st.session_state[f"{prefix}_available_minutes"])

    goals = list(cast(list[DevelopmentDomain], st.session_state[f"{prefix}_goals"]))
    constraints = list(cast(list[str], st.session_state[f"{prefix}_constraints"]))
    available_materials = list(
        cast(list[str], st.session_state[f"{prefix}_available_materials"])
    )
    if prefix == "form":
        constraints_optional = _optional_csv_items(
            str(st.session_state.get("form_constraints_optional", ""))
        )
        extra_context_raw = str(st.session_state.get("form_extra_context", ""))
        extra_context, _ = _truncate_text_with_limit(
            extra_context_raw,
            max_chars=int(st.session_state.get("cfg_max_input_chars", 4000)),
        )
        constraints = list(dict.fromkeys(constraints + constraints_optional))
        if extra_context:
            constraints = list(
                dict.fromkeys(constraints + [f"Kontext / Context: {extra_context}"])
            )

    return ActivitySearchCriteria(
        plz=str(st.session_state[f"{prefix}_plz"]),
        radius_km=float(st.session_state[f"{prefix}_radius_km"]),
        date=target_date,
        time_window=TimeWindow(
            start=start_time,
            end=(
                datetime.combine(target_date, start_time)
                + timedelta(minutes=available_minutes)
            ).time(),
        ),
        effort=cast(
            Literal["niedrig", "mittel", "hoch"],
            st.session_state[f"{prefix}_effort"],
        ),
        budget_eur_max=float(st.session_state[f"{prefix}_budget_eur_max"]),
        topics=list(cast(list[str], st.session_state[f"{prefix}_topics"])),
        location_preference=cast(
            Literal["indoor", "outdoor", "mixed"],
            st.session_state[f"{prefix}_location_preference"],
        ),
        goals=goals if goals else [DevelopmentDomain.language],
        constraints=constraints,
        available_materials=available_materials,
    )


def _criteria_sidebar(
    cfg: AppConfig,
) -> tuple[Optional[ActivitySearchCriteria], Language, FamilyProfile]:
    # Developer navigation: Sidebar is a UI adapter.
    # It initializes adapter keys once from criteria and writes changes back to criteria.
    criteria = get_criteria_state(cfg, key=CRITERIA_DAILY_KEY)
    _ensure_ui_adapter_state(prefix="sidebar", criteria=criteria)

    st.sidebar.header("Suche")
    lang: Language = st.sidebar.selectbox(
        "Sprache", options=["DE"], index=0, key="lang"
    )
    st.sidebar.date_input(
        _t(lang, "Datum", ""),
        key="sidebar_date",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.time_input(
        _t(lang, "Startzeit", ""),
        key="sidebar_start_time",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.select_slider(
        _t(
            lang,
            "Verfügbare Zeit (Minuten) / Available time (minutes)",
            "Verfügbare Zeit (Minuten) / Available time (minutes)",
        ),
        options=list(DURATION_OPTIONS),
        key="sidebar_available_minutes",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.text_input(
        _t(lang, "PLZ", ""),
        help=_t(
            lang,
            "5-stellige deutsche PLZ (z. B. 40215).",
            "",
        ),
        key="sidebar_plz",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.slider(
        "Radius (km)",
        min_value=0.5,
        max_value=50.0,
        step=0.5,
        key="sidebar_radius_km",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.selectbox(
        _t(lang, "Aufwand", ""),
        options=["niedrig", "mittel", "hoch"],
        format_func=lambda x: effort_label(x, lang),
        key="sidebar_effort",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.number_input(
        _t(lang, "Budget (max €)", "Budget (max €)"),
        min_value=0.0,
        max_value=250.0,
        step=1.0,
        key="sidebar_budget_eur_max",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.multiselect(
        _t(lang, "Themen / Topics", "Themen / Topics"),
        options=theme_options(lang),
        format_func=lambda x: theme_label(x, lang),
        key="sidebar_topics",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.segmented_control(
        _t(lang, "Ort / Location", "Ort / Location"),
        options=["mixed", "outdoor", "indoor"],
        format_func=lambda opt: {
            "mixed": "Gemischt / Mixed",
            "outdoor": "Draußen / Outdoor",
            "indoor": "Drinnen / Indoor",
        }[opt],
        key="sidebar_location_preference",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.multiselect(
        _t(lang, "Ziele / Goals", "Ziele / Goals"),
        options=list(GOAL_OPTIONS),
        format_func=lambda goal: DOMAIN_LABELS[cast(DevelopmentDomain, goal)],
        max_selections=2,
        key="sidebar_goals",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.multiselect(
        _t(lang, "Rahmenbedingungen / Constraints", "Rahmenbedingungen / Constraints"),
        options=list(CONSTRAINT_OPTIONS),
        key="sidebar_constraints",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )
    st.sidebar.multiselect(
        _t(
            lang,
            "Haushaltsmaterialien (verfügbar) / Household materials (available)",
            "Haushaltsmaterialien (verfügbar) / Household materials (available)",
        ),
        options=list(MATERIAL_OPTIONS),
        format_func=_material_label,
        key="sidebar_available_materials",
        on_change=_sync_widget_change_to_criteria,
        kwargs={"prefix": "sidebar", "state_key": CRITERIA_DAILY_KEY},
    )

    st.session_state["use_weather"] = st.sidebar.toggle(
        _t(lang, "Wetter berücksichtigen", ""),
        value=st.session_state.get("use_weather", True),
    )
    st.session_state["use_ai"] = st.sidebar.toggle(
        _t(lang, "KI-Text (OpenAI) nutzen", ""),
        value=st.session_state.get("use_ai", cfg.enable_llm),
    )
    st.session_state["offline_mode"] = st.sidebar.toggle(
        _t(
            lang,
            "Offline-Modus (ohne LLM) / Offline mode (no LLM)",
            "Offline-Modus (ohne LLM) / Offline mode (no LLM)",
        ),
        value=st.session_state.get("offline_mode", False),
    )
    st.session_state["plan_mode"] = st.sidebar.selectbox(
        _t(lang, "Plan-Modus / Plan mode", "Plan mode"),
        options=["standard", "parent_script"],
        format_func=lambda value: (
            "Standard"
            if value == "standard"
            else "Elternskript (kurz, wiederholbar) / Parent script (short, repeatable)"
        ),
        index=0 if st.session_state.get("plan_mode", "standard") == "standard" else 1,
    )

    st.sidebar.divider()
    st.sidebar.subheader(_t(lang, "Familie / Family", "Familie / Family"))
    st.sidebar.caption(
        _t(
            lang,
            "Bitte gib nicht den vollständigen Namen deines Kindes oder identifizierende Informationen ein.",
            "Don't enter your child's full name or identifying info.",
        )
    )
    child_name = (
        st.sidebar.text_input(
            _t(lang, "Name des Kindes / Child name", "Name des Kindes / Child name"),
            value=st.session_state.get("profile_child_name", "Carla"),
            key="profile_child_name",
        ).strip()
        or "Carla"
    )
    parent_names = (
        st.sidebar.text_input(
            _t(
                lang,
                "Name der Eltern / Parent name(s)",
                "Name der Eltern / Parent name(s)",
            ),
            value=st.session_state.get("profile_parent_names", "Miri"),
            key="profile_parent_names",
        ).strip()
        or "Miri"
    )
    age_band_labels = [label for label, _ in AGE_BAND_OPTIONS]
    age_band_map = dict(AGE_BAND_OPTIONS)
    current_age = float(st.session_state.get("profile_child_age_years", 2.5))
    current_band = min(AGE_BAND_OPTIONS, key=lambda item: abs(item[1] - current_age))[0]
    selected_age_band = st.sidebar.selectbox(
        _t(
            lang,
            "Altersband / Age band",
            "Altersband / Age band",
        ),
        options=age_band_labels,
        index=age_band_labels.index(current_band),
        key="profile_child_age_band",
    )
    child_age_years = age_band_map[selected_age_band]
    st.session_state["profile_child_age_years"] = float(child_age_years)
    family_profile = FamilyProfile(
        child_name=child_name,
        parent_names=parent_names,
        child_age_years=float(child_age_years),
    )

    try:
        criteria = _build_criteria_from_widget_state(prefix="sidebar")
        st.session_state[CRITERIA_DAILY_KEY] = criteria
        return criteria, lang, family_profile
    except ValidationError as exc:
        st.sidebar.error(_t(lang, "Ungültige Eingaben:", ""))
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []))
            st.sidebar.write(f"- `{loc}`: {err.get('msg', 'invalid')}")
        return (
            None,
            lang,
            FamilyProfile(child_name="Carla", parent_names="Miri", child_age_years=2.5),
        )


def _generate_activity_plan_with_retry(
    cfg: AppConfig,
    picked: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
    lang: Language,
    plan_mode: Literal["standard", "parent_script"],
) -> ActivityPlan:
    attempts = 3
    wait_s = 1.0
    last_err: Optional[Exception] = None

    if not _consume_request_budget(cfg, lang=lang, scope="activity-plan"):
        cfg_payload = {**cfg.__dict__, "enable_llm": False}
        return generate_activity_plan(
            cfg.__class__(**cfg_payload),
            picked,
            criteria,
            weather,
            plan_mode=plan_mode,
        )

    cfg_payload = {**cfg.__dict__}
    if not st.session_state.get("use_ai", False):
        cfg_payload["enable_llm"] = False
    cfg_runtime = cfg.__class__(**cfg_payload)

    for _ in range(attempts):
        try:
            return generate_activity_plan(
                cfg_runtime,
                picked,
                criteria,
                weather,
                plan_mode=plan_mode,
            )
        except ActivityGenerationError as exc:
            last_err = exc
            time_module.sleep(wait_s)
            wait_s *= 2

    st.error(
        _t(
            lang,
            "Die Plan-Erstellung ist gerade fehlgeschlagen. Wir zeigen eine sichere Fallback-Version an. / Plan generation failed right now. Showing a safe fallback version.",
            "",
        )
    )
    if last_err:
        st.caption(str(last_err))
    cfg_payload["enable_llm"] = False
    return generate_activity_plan(
        cfg.__class__(**cfg_payload),
        picked,
        criteria,
        weather,
        plan_mode=plan_mode,
    )


def _split_daily_markdown(markdown: str) -> tuple[str, str]:
    lines = markdown.splitlines()
    content_lines = [line for line in lines if line.strip()]
    if len(content_lines) < 4:
        return markdown, ""

    preview_candidates = content_lines[:4]
    remaining_preview = list(preview_candidates)
    preview_lines: list[str] = []
    details_lines: list[str] = []

    for line in lines:
        if remaining_preview and line == remaining_preview[0]:
            preview_lines.append(line)
            remaining_preview.pop(0)
            continue
        details_lines.append(line)

    preview = "\n".join(preview_lines).strip()
    details = "\n".join(details_lines).strip()
    return preview, details


def _render_adventure_details(a: MicroAdventure, lang: Language) -> None:
    st.markdown(f"**{a.title}**  \n{a.short}")
    cols = st.columns(4)
    cols[0].metric(_t(lang, "Dauer", ""), f"{a.duration_minutes} min")
    cols[1].metric(_t(lang, "Distanz", ""), f"{a.distance_km:.1f} km")
    cols[2].metric(_t(lang, "Kinderwagen", ""), "✅" if a.stroller_ok else "—")
    cols[3].metric(_t(lang, "Sicherheit", ""), a.safety_level)

    st.markdown("### " + _t(lang, "Startpunkt", ""))
    st.write(a.start_point)

    st.markdown("### " + _t(lang, "Ablauf", ""))
    for step in a.route_steps:
        st.write(f"- {step}")


def _render_export_block(
    picked: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
    markdown: str,
    lang: Language,
) -> None:
    st.subheader(_t(lang, "Export", ""))
    json_payload = {
        "criteria": criteria.model_dump(mode="json"),
        "weather": weather.__dict__ if weather else None,
        "adventure": picked.__dict__,
        "markdown": markdown,
    }
    st.download_button(
        label=_t(lang, "JSON herunterladen", ""),
        data=json.dumps(json_payload, ensure_ascii=False, indent=2, default=str),
        file_name=f"mikroabenteuer-{criteria.date.isoformat()}.json",
        mime="application/json",
    )
    st.download_button(
        label=_t(lang, "Markdown herunterladen", ""),
        data=markdown,
        file_name=f"mikroabenteuer-{criteria.date.isoformat()}.md",
        mime="text/markdown",
    )

    ics_bytes = build_ics_event(
        day=criteria.date,
        summary=f"Mikroabenteuer: {picked.title}",
        description=markdown,
        location=picked.area,
        tzid="Europe/Berlin",
        start_time_local=criteria.start_time,
        duration_minutes=picked.duration_minutes,
    )
    st.download_button(
        label="ICS herunterladen",
        data=ics_bytes,
        file_name="mikroabenteuer.ics",
        mime="text/calendar",
    )

    email_html = render_daily_email_html(
        picked, criteria, criteria.date, markdown, weather
    )
    with st.expander(_t(lang, "E-Mail-Vorschau", ""), expanded=False):
        st.caption(
            _t(
                lang,
                "So sieht die E-Mail im Postfach aus. Den HTML-Code kannst du optional unten aufklappen.",
                "",
            )
        )
        components.html(email_html, height=680, scrolling=True)

        with st.expander(_t(lang, "HTML-Code anzeigen", "")):
            st.code(
                email_html[:3000] + ("..." if len(email_html) > 3000 else ""),
                language="html",
            )


def _render_automation_block(
    cfg: AppConfig, criteria: ActivitySearchCriteria, lang: Language
) -> None:
    with st.expander(_t(lang, "Automatisierung (optional)", ""), expanded=False):
        send_email = st.checkbox("E-Mail senden", value=False)
        create_calendar_event = st.checkbox("Kalendereintrag erstellen", value=False)
        if st.button("Daily-Job jetzt ausführen"):
            try:
                result = run_daily_job_once(
                    cfg,
                    criteria,
                    send_email=send_email,
                    create_calendar_event=create_calendar_event,
                )
                st.success(f"OK: {result.subject} -> {result.to_email or 'n/a'}")
            except Exception as exc:
                st.error(
                    _t(
                        lang,
                        f"Automatisierung fehlgeschlagen: {exc}",
                        "",
                    )
                )


@dataclass
class OpenAIActivityService:
    cfg: AppConfig

    def search_events(
        self,
        criteria: ActivitySearchCriteria,
        weather: Optional[WeatherSummary],
        mode: str,
    ) -> dict[str, Any]:
        try:
            from src.mikroabenteuer.openai_activity_service import suggest_activities

            event_weather: EventWeatherSummary | None = None
            if weather is not None:
                event_weather = EventWeatherSummary(
                    condition=EventWeatherCondition.unknown,
                    summary_de_en="Wetter lokal geladen",
                    temperature_min_c=weather.temperature_min_c,
                    temperature_max_c=weather.temperature_max_c,
                    precipitation_probability_pct=(
                        int(weather.precipitation_probability_max)
                        if weather.precipitation_probability_max is not None
                        else None
                    ),
                    precipitation_sum_mm=weather.precipitation_sum_mm,
                    wind_speed_max_kmh=weather.windspeed_max_kmh,
                    country_code="DE",
                    city="Düsseldorf",
                    timezone=self.cfg.timezone,
                    data_source="open-meteo",
                )

            result = suggest_activities(
                criteria,
                mode="genau" if mode == "genau" else "schnell",
                base_url=os.getenv("OPENAI_BASE_URL") or None,
                timeout_s=self.cfg.timeout_s,
                max_input_chars=self.cfg.max_input_chars,
                max_output_tokens=self.cfg.max_output_tokens,
                weather=event_weather,
            )
            return {
                "suggestions": list(getattr(result, "suggestions", [])),
                "sources": list(getattr(result, "sources", [])),
                "warnings": list(getattr(result, "warnings_de_en", [])),
                "errors": list(getattr(result, "errors_de_en", [])),
            }
        except Exception as exc:
            return {
                "suggestions": [],
                "sources": [],
                "warnings": [f"OpenAI-Suche aktuell nicht verfügbar: {exc}"],
                "errors": [],
            }


@dataclass
class ActivityOrchestrator:
    cfg: AppConfig
    openai_service: OpenAIActivityService

    def run(
        self,
        criteria: ActivitySearchCriteria,
        *,
        mode: str,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> dict[str, Any]:
        warnings: list[str] = []

        if on_status:
            on_status("Wetter wird geladen …")
        weather: Optional[WeatherSummary] = None
        if st.session_state.get("use_weather", True):
            weather = _get_weather(criteria.date.isoformat(), self.cfg.timezone)

        if st.session_state.get("offline_mode", False):
            if on_status:
                on_status("Offline-Bibliothek wird durchsucht …")
            child_age_years = float(
                st.session_state.get("profile_child_age_years", 6.0)
            )
            suggestions, offline_warnings = suggest_activities_offline(
                criteria,
                child_age_years=child_age_years,
            )
            event_result = {
                "suggestions": suggestions,
                "sources": [],
                "warnings": offline_warnings
                + [
                    "Offline-Modus aktiv: Ergebnisse stammen aus data/activity_library.json. / Offline mode active: results are from data/activity_library.json."
                ],
                "errors": [],
            }
        else:
            if on_status:
                on_status("Veranstaltungen werden recherchiert …")
            if not _consume_request_budget(self.cfg, lang="DE", scope="events-search"):
                event_result = {
                    "suggestions": [],
                    "sources": [],
                    "warnings": [
                        "Session-Limit für API-Anfragen erreicht. / Session request limit reached."
                    ],
                    "errors": [],
                }
            else:
                event_result = self.openai_service.search_events(
                    criteria, weather, mode
                )
        warnings.extend(cast(list[str], event_result.get("warnings", [])))
        warnings.extend(cast(list[str], event_result.get("errors", [])))

        if on_status:
            on_status("Suche abgeschlossen")

        return {
            "weather": weather,
            "warnings": list(dict.fromkeys(warnings)),
            "events": event_result.get("suggestions", []),
            "sources": event_result.get("sources", []),
        }


@st.cache_resource(show_spinner=False)
def _get_activity_orchestrator(
    cfg: AppConfig,
) -> tuple[OpenAIActivityService, ActivityOrchestrator]:
    openai_service = OpenAIActivityService(cfg=cfg)
    return openai_service, ActivityOrchestrator(cfg=cfg, openai_service=openai_service)


def render_wetter_und_events_section(cfg: AppConfig, lang: Language) -> None:
    # Formular-Adapter folgt einer Einweg-Regel.
    # Interaktion schreibt nach criteria; Rendering liest nur für die Erstinitialisierung.
    criteria = get_criteria_state(cfg, key=CRITERIA_EVENTS_KEY)
    _ensure_ui_adapter_state(prefix="form", criteria=criteria)

    st.subheader(_t(lang, "Wetter & Veranstaltungen", ""))

    with st.form("weather_events_form", clear_on_submit=False):
        top_left, top_right = st.columns(2)
        with top_left:
            st.text_input(
                _t(lang, "PLZ", ""),
                key="form_plz",
                max_chars=5,
            )
            st.date_input(
                _t(lang, "Datum", ""),
                key="form_date",
            )
            st.time_input(
                _t(lang, "Startzeit", ""),
                key="form_start_time",
            )
            st.select_slider(
                _t(
                    lang,
                    "Zeitbudget (Minuten) / Duration",
                    "Zeitbudget (Minuten) / Duration",
                ),
                options=list(DURATION_OPTIONS),
                key="form_available_minutes",
            )
        with top_right:
            st.slider(
                _t(lang, "Radius (km)", "Radius (km)"),
                min_value=0.5,
                max_value=50.0,
                step=0.5,
                key="form_radius_km",
            )
            st.selectbox(
                _t(lang, "Aufwand", ""),
                options=["niedrig", "mittel", "hoch"],
                format_func=lambda x: effort_label(x, lang),
                key="form_effort",
            )
            st.number_input(
                _t(lang, "Budget (max €)", "Budget (max €)"),
                min_value=0.0,
                max_value=250.0,
                step=1.0,
                key="form_budget_eur_max",
            )
            st.multiselect(
                _t(lang, "Themen / Topics", "Themen / Topics"),
                options=theme_options(lang),
                format_func=lambda x: theme_label(x, lang),
                key="form_topics",
            )
            st.toggle(
                _t(
                    lang,
                    "Ort: draußen bevorzugen / Prefer outdoor",
                    "Ort: draußen bevorzugen / Prefer outdoor",
                ),
                key="form_pref_outdoor",
                value=st.session_state.get("form_location_preference", "mixed")
                == "outdoor",
            )
            st.toggle(
                _t(
                    lang,
                    "Ort: drinnen bevorzugen / Prefer indoor",
                    "Ort: drinnen bevorzugen / Prefer indoor",
                ),
                key="form_pref_indoor",
                value=st.session_state.get("form_location_preference", "mixed")
                == "indoor",
            )
            st.multiselect(
                _t(lang, "Ziele / Goals", "Ziele / Goals"),
                options=list(GOAL_OPTIONS),
                format_func=lambda goal: DOMAIN_LABELS[cast(DevelopmentDomain, goal)],
                max_selections=2,
                key="form_goals",
            )
            st.multiselect(
                _t(
                    lang,
                    "Rahmenbedingungen / Constraints",
                    "Rahmenbedingungen / Constraints",
                ),
                options=list(CONSTRAINT_OPTIONS),
                key="form_constraints",
            )
            st.multiselect(
                _t(
                    lang,
                    "Haushaltsmaterialien (verfügbar) / Household materials (available)",
                    "Haushaltsmaterialien (verfügbar) / Household materials (available)",
                ),
                options=list(MATERIAL_OPTIONS),
                format_func=_material_label,
                key="form_available_materials",
            )
            st.text_input(
                _t(
                    lang,
                    "Weitere Rahmenbedingungen (optional, max 80) / Other constraints (optional, max 80)",
                    "Weitere Rahmenbedingungen (optional, max 80) / Other constraints (optional, max 80)",
                ),
                key="form_constraints_optional",
                max_chars=80,
            )
            st.text_area(
                _t(
                    lang,
                    "Zusätzlicher Kontext / Extra context",
                    "Zusätzlicher Kontext / Extra context",
                ),
                key="form_extra_context",
                help=_t(
                    lang,
                    f"Wird auf {cfg.max_input_chars} Zeichen begrenzt. / Limited to {cfg.max_input_chars} characters.",
                    "",
                ),
            )

        mode = st.radio(
            _t(lang, "Genauigkeit", ""),
            options=["schnell", "genau"],
            format_func=lambda m: (
                _t(lang, "Schnell", "") if m == "schnell" else _t(lang, "Genau", "")
            ),
            horizontal=True,
        )

        pref_outdoor = bool(st.session_state.get("form_pref_outdoor", False))
        pref_indoor = bool(st.session_state.get("form_pref_indoor", False))
        if pref_outdoor and pref_indoor:
            st.session_state["form_location_preference"] = "mixed"
        elif pref_outdoor:
            st.session_state["form_location_preference"] = "outdoor"
        elif pref_indoor:
            st.session_state["form_location_preference"] = "indoor"
        else:
            st.session_state["form_location_preference"] = "mixed"

        extra_context_raw = str(st.session_state.get("form_extra_context", ""))
        if len(extra_context_raw) > cfg.max_input_chars:
            st.warning(
                _t(
                    lang,
                    f"Zusätzlicher Kontext wird bei Anfrage auf {cfg.max_input_chars} Zeichen gekürzt. / Extra context will be truncated to {cfg.max_input_chars} characters when requested.",
                    "",
                )
            )

        submitted = st.form_submit_button(
            _t(lang, "Wetter und Veranstaltungen laden", "")
        )

    if submitted:
        try:
            _sync_widget_change_to_criteria(
                prefix="form",
                state_key=CRITERIA_EVENTS_KEY,
                raise_on_error=True,
            )
            st.session_state["weather_events_submitted"] = True
            st.rerun()
        except ValidationError as exc:
            st.error(
                _t(
                    lang,
                    "Bitte prüfe die Eingaben. Details siehe unten.",
                    "",
                )
            )
            for err in exc.errors():
                loc = ".".join(str(p) for p in err.get("loc", []))
                st.write(f"- `{loc}`: {err.get('msg', 'invalid')}")
            return

    if not st.session_state.pop("weather_events_submitted", False):
        return

    criteria = get_criteria_state(cfg, key=CRITERIA_EVENTS_KEY)
    _service, orchestrator = _get_activity_orchestrator(cfg)
    status_box = st.empty()

    def _status_update(message: str) -> None:
        status_box.info(message)

    payload = orchestrator.run(criteria, mode=mode, on_status=_status_update)
    status_box.success(_t(lang, "Fertig.", ""))

    weather = payload.get("weather")
    if weather:
        st.markdown("#### " + _t(lang, "Wetter", ""))
        st.write(
            _t(
                lang,
                f"Tags: {', '.join(weather.derived_tags)}",
                f"Tags: {', '.join(weather.derived_tags)}",
            )
        )

    warnings = payload.get("warnings", [])
    if warnings:
        st.markdown("#### " + _t(lang, "Hinweise", ""))
        for warning in warnings:
            st.warning(str(warning))

    events = payload.get("events", [])
    st.markdown("#### " + _t(lang, "Veranstaltungen", ""))
    if not events:
        st.info(
            _t(
                lang,
                "Aktuell keine Treffer bei Veranstaltungen. Bitte Radius/Themen anpassen.",
                "",
            )
        )
    for event in events:
        title = str(getattr(event, "title", _t(lang, "Vorschlag", "")))
        reason = str(getattr(event, "reason_de_en", ""))
        st.markdown(f"- **{title}** — {reason}")

    sources = payload.get("sources", [])
    if sources:
        st.markdown("#### " + _t(lang, "Quellen", ""))
        for source in sources:
            st.markdown(f"- {source}")


def main() -> None:
    try:
        cfg = load_runtime_config()
    except ValidationError as error:
        render_missing_config_ui(error)
        return
    st.session_state["cfg_max_input_chars"] = int(cfg.max_input_chars)
    inject_custom_styles(ROOT / "Hintergrund.png")

    default_profile = FamilyProfile(
        child_name=str(st.session_state.get("profile_child_name", "Carla")),
        parent_names=str(st.session_state.get("profile_parent_names", "Miri")),
        child_age_years=float(st.session_state.get("profile_child_age_years", 2.5)),
    )
    st.title(_replace_family_tokens("Mikroabenteuer mit Carla", default_profile))
    top_col_left, top_col_center, top_col_right = st.columns([1, 1.6, 1])
    with top_col_center:
        st.image(image="ChatGPT Image 14. Feb. 2026, 20_05_20.png", width=240)

    criteria, lang, family_profile = _criteria_sidebar(cfg)
    adventures = _load_adventures()

    if criteria is None:
        st.warning(_t(lang, "Bitte Eingaben korrigieren.", ""))
        st.stop()

    weather: Optional[WeatherSummary] = None
    if st.session_state.get("use_weather", True):
        weather = _get_weather(criteria.date.isoformat(), cfg.timezone)

    picked, _candidates = pick_daily_adventure(adventures, criteria, weather)
    picked = _profiled_adventure(picked, family_profile)

    st.subheader(_t(lang, "Abenteuer des Tages", ""))
    if weather:
        st.caption(
            _t(
                lang,
                f"Wetter-Tags: {', '.join(weather.derived_tags)}",
                "",
            )
        )

    activity_plan = _generate_activity_plan_with_retry(
        cfg,
        picked,
        criteria,
        weather,
        lang,
        plan_mode=cast(
            Literal["standard", "parent_script"],
            st.session_state.get("plan_mode", "standard"),
        ),
    )
    activity_plan = activity_plan.model_copy(
        update={
            "title": _replace_family_tokens(activity_plan.title, family_profile),
            "summary": _replace_family_tokens(activity_plan.summary, family_profile),
            "steps": [
                _replace_family_tokens(s, family_profile) for s in activity_plan.steps
            ],
            "safety_notes": [
                _replace_family_tokens(s, family_profile)
                for s in activity_plan.safety_notes
            ],
            "parent_child_prompts": [
                _replace_family_tokens(s, family_profile)
                for s in activity_plan.parent_child_prompts
            ],
            "variants": [
                _replace_family_tokens(s, family_profile)
                for s in activity_plan.variants
            ],
        }
    )
    daily_md = render_activity_plan_markdown(activity_plan)
    daily_preview_md, daily_details_md = _split_daily_markdown(daily_md)
    st.markdown(daily_preview_md)
    if daily_details_md:
        with st.expander(
            _t(lang, "Details anzeigen / ausblenden", ""),
            expanded=False,
        ):
            st.markdown(daily_details_md)

    st.markdown("#### " + _t(lang, "Plan melden / Report plan", ""))
    report_reason = st.selectbox(
        _t(lang, "Grund / Reason", ""),
        options=REPORT_REASONS,
        key="plan_report_reason",
    )
    if st.button(_t(lang, "Diesen Plan melden / Report this plan", "")):
        report = save_plan_report(activity_plan, report_reason)
        st.success(
            _t(
                lang,
                f"Meldung gespeichert ({report.timestamp_utc}). Keine Personenangaben wurden gespeichert. / Report saved ({report.timestamp_utc}). No personal data was stored.",
                "",
            )
        )

    with st.expander(
        _t(lang, "Gemeldete Pläne ansehen / Review reported plans", ""),
        expanded=False,
    ):
        reports = load_plan_reports(limit=100)
        if reports:
            st.dataframe(reports, width="stretch", hide_index=True)
        else:
            st.caption(
                _t(lang, "Noch keine Meldungen vorhanden. / No reports yet.", "")
            )

    st.divider()
    render_wetter_und_events_section(cfg, lang)

    _render_export_block(picked, criteria, weather, daily_md, lang)
    _render_automation_block(cfg, criteria, lang)

    st.divider()
    st.subheader(_t(lang, "Bibliothek", ""))
    filtered = filter_adventures(adventures, criteria)
    st.caption(
        _t(
            lang,
            f"{len(filtered)} passende Abenteuer (von {len(adventures)}).",
            "",
        )
    )
    st.dataframe(
        [_profiled_adventure(a, family_profile).summary_row() for a in filtered],
        width="stretch",
        hide_index=True,
    )

    for a in filtered:
        profiled_adventure = _profiled_adventure(a, family_profile)
        with st.expander(
            f"{profiled_adventure.title} · {profiled_adventure.area} · {profiled_adventure.duration_minutes} min",
            expanded=False,
        ):
            _render_adventure_details(profiled_adventure, lang)

    if os.getenv("ENABLE_DAILY_SCHEDULER", "0") == "1":
        st.info(
            _t(
                lang,
                "Hinweis: Geplanter Scheduler bitte in separatem Prozess via start_scheduler_0820 nutzen.",
                "",
            )
        )


if __name__ == "__main__":
    main()
