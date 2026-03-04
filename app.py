# ruff: noqa: E402
from __future__ import annotations

import base64
import hashlib
import json
import os
import time as time_module
from datetime import date, datetime, time, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional, cast

import re

import requests
import streamlit as st
import streamlit.components.v1 as components
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent

from mikroabenteuer.config import AppConfig
from mikroabenteuer.constants import (
    Language,
    effort_label,
    theme_label,
    theme_options,
)
from mikroabenteuer.data_seed import seed_adventures
from mikroabenteuer.email_templates import render_daily_email_html
from mikroabenteuer.activity_library import suggest_activities_offline
from mikroabenteuer.ics import build_ics_event
from mikroabenteuer.materials import (
    COMMON_HOUSEHOLD_MATERIALS,
    MATERIAL_LABELS,
)
from mikroabenteuer.models import (
    ActivitySearchCriteria,
    DevelopmentDomain,
    TimeWindow,
    WeatherCondition as EventWeatherCondition,
    WeatherSummary as EventWeatherSummary,
    ActivityPlan,
    MicroAdventure,
)
from mikroabenteuer.openai_gen import (
    ActivityGenerationError,
    generate_activity_plan,
    render_activity_plan_markdown,
)
from mikroabenteuer.openai_activity_service import (
    ERROR_CODE_API_NON_RETRYABLE,
    ERROR_CODE_MISSING_API_KEY,
    ERROR_CODE_RETRYABLE_UPSTREAM,
    ERROR_CODE_STRUCTURED_OUTPUT,
    VALIDATION_DETAIL_PREFIX,
)
from mikroabenteuer.plan_reports import (
    REPORT_REASONS,
    load_plan_reports,
    save_plan_report,
)
from mikroabenteuer.recommender import pick_daily_adventure
from mikroabenteuer.scheduler import run_daily_job_once
from mikroabenteuer.settings import load_runtime_config, render_missing_config_ui
from mikroabenteuer.weather import WeatherSummary, fetch_weather_for_day
from mikroabenteuer.ui.filter_specs import (
    FilterFieldSpec,
    build_core_filter_specs,
    render_filter_fields,
)
from mikroabenteuer.ui.state_keys import CriteriaKeySpace, CriteriaNamespace


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
    DevelopmentDomain.gross_motor: "Grobmotorik",
    DevelopmentDomain.fine_motor: "Feinmotorik",
    DevelopmentDomain.language: "Sprache",
    DevelopmentDomain.social_emotional: "Sozial-emotional",
    DevelopmentDomain.sensory: "Sensorik",
    DevelopmentDomain.cognitive: "Kognitiv",
}
CONSTRAINT_OPTIONS: tuple[str, ...] = (
    "Kein Auto",
    "Kinderwagen",
    "Wetterfest",
    "Niedriges Budget",
    "Reizarm",
    "Barrierearm",
)

MATERIAL_OPTIONS: tuple[str, ...] = COMMON_HOUSEHOLD_MATERIALS

CORE_FILTER_SPECS: tuple[FilterFieldSpec, ...] = build_core_filter_specs(
    duration_options=DURATION_OPTIONS,
    effort_options=("niedrig", "mittel", "hoch"),
    goal_options=GOAL_OPTIONS,
    constraint_options=CONSTRAINT_OPTIONS,
    material_options=MATERIAL_OPTIONS,
    theme_options_factory=theme_options,
)


def _core_specs_by_id(*ids: str) -> tuple[FilterFieldSpec, ...]:
    wanted = set(ids)
    return tuple(spec for spec in CORE_FILTER_SPECS if spec.id in wanted)


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
                f"Session-Limit erreicht ({cfg.max_requests_per_session} Anfragen). Bitte Seite neu laden.",
                "",
            )
        )
        return False

    st.session_state["request_count"] = count + 1
    current = int(st.session_state["request_count"])
    st.caption(
        _t(
            lang,
            f"Anfragebudget {current}/{cfg.max_requests_per_session} ({scope}).",
            "",
        )
    )
    return True


@st.cache_data(show_spinner=False)
def _read_background_b64(background_path: str) -> str:
    return base64.b64encode(Path(background_path).read_bytes()).decode("utf-8")


@st.cache_data(show_spinner=False, ttl=24 * 60 * 60)
def _resolve_location_from_plz(
    plz: str,
    *,
    timeout_s: float = 6.0,
) -> dict[str, str] | None:
    """Resolve a German postal code to coarse user-location metadata."""
    try:
        response = requests.get(
            f"https://api.zippopotam.us/de/{plz}",
            timeout=timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    places = payload.get("places") or []
    if not places:
        return None

    first_place = places[0]
    city = str(first_place.get("place name") or "").strip()
    region = str(first_place.get("state") or "").strip()
    country_code = str(payload.get("country abbreviation") or "").strip()

    if not city or not region or not country_code:
        return None

    return {
        "city": city,
        "region": region,
        "country_code": country_code,
    }


def inject_custom_styles(background_path: Path) -> None:
    if not background_path.exists():
        return

    background_b64 = _read_background_b64(str(background_path))
    st.markdown(
        f"""
        <style>
            :root {{
                --primary-dark-green: #00715D;
                --primary-mint: #A4D4AE;
                --primary-mint-soft: #d7efdc;
                --primary-dark-green-hover: #005f4f;
                --accent-terracotta: #D98556;
                --accent-marigold: #F4B400;
                --secondary-sky-blue: #80C7CF;
                --secondary-lavender: #B8B1D3;
                --background-cream: #F9F4E7;
                --text-charcoal: #2F353D;
                --text-muted: #5f6873;
                --line-soft: #E3E6E9;
                --surface-soft: #ffffff;
                --surface-soft-hover: #f6f8fa;
                --focus-ring: #0c8f78;
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
                background-color: var(--primary-dark-green-hover) !important;
                color: #ffffff !important;
                border-color: #004d40 !important;
            }}
            .stDownloadButton button:disabled {{
                background-color: var(--line-soft) !important;
                color: var(--text-muted) !important;
                border-color: #c7cfd4 !important;
            }}
            .stTextInput input,
            .stNumberInput input,
            .stDateInput input,
            .stTimeInput input,
            .stTextArea textarea,
            .stSelectbox [data-baseweb="select"] > div,
            .stSelectbox [data-baseweb="select"] > div > div,
            .stSelectbox [data-baseweb="select"] [role="combobox"],
            .stMultiSelect [data-baseweb="tag"] {{
                background-color: var(--surface-soft) !important;
                color: var(--text-charcoal) !important;
                border: 1px solid #b9c5cc !important;
            }}
            .stMultiSelect [data-baseweb="select"] > div,
            .stMultiSelect [data-baseweb="select"] > div > div,
            .stMultiSelect [data-baseweb="select"] [role="combobox"],
            .stMultiSelect [data-baseweb="select"] input {{
                background-color: var(--surface-soft) !important;
                color: var(--text-charcoal) !important;
            }}
            .stSelectbox [data-baseweb="select"] > div:hover,
            .stMultiSelect [data-baseweb="select"] > div:hover {{
                background-color: var(--surface-soft-hover) !important;
            }}
            .stTextInput input::placeholder,
            .stNumberInput input::placeholder,
            .stTextArea textarea::placeholder {{
                color: var(--text-muted) !important;
                opacity: 1 !important;
            }}
            .stSelectbox [data-baseweb="select"] span,
            .stMultiSelect [data-baseweb="select"] span,
            .stSelectbox [data-baseweb="select"] svg,
            .stMultiSelect [data-baseweb="select"] svg,
            .stDateInput span,
            .stTimeInput span {{
                color: var(--text-charcoal) !important;
                fill: var(--text-charcoal) !important;
            }}
            .stSlider [data-baseweb="slider"] > div > div {{
                background-color: var(--line-soft) !important;
            }}
            .stSlider [data-baseweb="slider"] [role="slider"] {{
                background-color: #ff5d5d !important;
                border: 2px solid #ffffff !important;
                box-shadow: 0 0 0 2px rgba(255, 93, 93, 0.35) !important;
            }}
            .stTextInput input:focus,
            .stNumberInput input:focus,
            .stDateInput input:focus,
            .stTimeInput input:focus,
            .stTextArea textarea:focus,
            .stSelectbox [data-baseweb="select"] > div:focus-within,
            .stMultiSelect [data-baseweb="select"] > div:focus-within {{
                border-color: var(--focus-ring) !important;
                box-shadow: 0 0 0 1px var(--focus-ring) !important;
            }}
            [data-baseweb="tag"] {{
                background-color: #ffe1e1 !important;
                color: #8a1f1f !important;
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
            [data-testid="stMarkdownContainer"] code {{
                background-color: var(--primary-mint-soft) !important;
                color: #1f2933 !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _load_adventures() -> list[MicroAdventure]:
    return seed_adventures()


@st.cache_data(show_spinner=False, ttl=1800)
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
    # Interaktionsmodell (einheitlich): Kernfilter werden in beiden Bereichen per on-change
    # in den Criteria-State gespiegelt. Explizite Buttons starten nur teure Folgeaktionen.
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
    "child_age_years",
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
        "child_age_years": float(criteria.child_age_years),
        "topics": list(criteria.topics),
        "location_preference": criteria.location_preference,
        "goals": list(criteria.goals),
        "constraints": list(criteria.constraints),
        "available_materials": list(criteria.available_materials),
    }


def _ensure_ui_adapter_state(
    namespace: CriteriaNamespace, criteria: ActivitySearchCriteria
) -> None:
    keys = CriteriaKeySpace(namespace)
    widget_values = _criteria_to_widget_values(criteria)
    for field in CRITERIA_WIDGET_FIELDS:
        key = keys.widget(field)
        if key not in st.session_state:
            st.session_state[key] = widget_values[field]


def _sync_widget_change_to_criteria(
    namespace: CriteriaNamespace,
    *,
    state_key: str,
    raise_on_error: bool = False,
) -> None:
    try:
        st.session_state[state_key] = _build_criteria_from_widget_state(
            namespace=namespace
        )
    except ValidationError:
        if raise_on_error:
            raise
        return


@dataclass(frozen=True)
class NormalizedWidgetInput:
    plz: str
    radius_km: float
    date_value: date
    start_time: time
    available_minutes: int
    effort: Literal["niedrig", "mittel", "hoch"]
    budget_eur_max: float
    child_age_years: float
    topics: list[str]
    location_preference: Literal["indoor", "outdoor", "mixed"]
    goals: list[DevelopmentDomain]
    constraints: list[str]
    available_materials: list[str]


def _collect_widget_raw_values(namespace: CriteriaNamespace) -> dict[str, Any]:
    keys = CriteriaKeySpace(namespace)
    raw_values: dict[str, Any] = {
        "plz": st.session_state[keys.widget("plz")],
        "radius_km": st.session_state[keys.widget("radius_km")],
        "date": st.session_state[keys.widget("date")],
        "start_time": st.session_state[keys.widget("start_time")],
        "available_minutes": st.session_state[keys.widget("available_minutes")],
        "effort": st.session_state[keys.widget("effort")],
        "budget_eur_max": st.session_state[keys.widget("budget_eur_max")],
        "child_age_years": st.session_state[keys.widget("child_age_years")],
        "topics": st.session_state[keys.widget("topics")],
        "location_preference": st.session_state[keys.widget("location_preference")],
        "goals": st.session_state[keys.widget("goals")],
        "constraints": st.session_state[keys.widget("constraints")],
        "available_materials": st.session_state[keys.widget("available_materials")],
        "constraints_optional": st.session_state.get(
            keys.widget("constraints_optional"), ""
        ),
        "extra_context": st.session_state.get(keys.widget("extra_context"), ""),
    }
    if namespace == "events":
        raw_values["pref_outdoor"] = st.session_state.get(
            keys.widget("pref_outdoor"), False
        )
        raw_values["pref_indoor"] = st.session_state.get(
            keys.widget("pref_indoor"), False
        )
    return raw_values


def _normalize_location_preference(
    raw_values: dict[str, Any], *, mode: CriteriaNamespace
) -> Literal["indoor", "outdoor", "mixed"]:
    if mode != "events":
        return cast(
            Literal["indoor", "outdoor", "mixed"],
            str(raw_values.get("location_preference", "mixed")),
        )

    pref_outdoor = bool(raw_values.get("pref_outdoor", False))
    pref_indoor = bool(raw_values.get("pref_indoor", False))
    if pref_outdoor and pref_indoor:
        return "mixed"
    if pref_outdoor:
        return "outdoor"
    if pref_indoor:
        return "indoor"
    return "mixed"


def _normalize_optional_constraints(raw_values: dict[str, Any]) -> list[str]:
    return _optional_csv_items(str(raw_values.get("constraints_optional", "")))


def _normalize_extra_context_constraint(
    raw_values: dict[str, Any], *, max_input_chars: int
) -> list[str]:
    extra_context_raw = str(raw_values.get("extra_context", ""))
    extra_context, _ = _truncate_text_with_limit(
        extra_context_raw,
        max_chars=max_input_chars,
    )
    if not extra_context:
        return []
    return [f"Kontext: {extra_context}"]


def normalize_widget_input(
    raw_values: dict[str, Any],
    *,
    mode: CriteriaNamespace,
    max_input_chars: int,
) -> NormalizedWidgetInput:
    constraints = list(cast(list[str], raw_values.get("constraints", [])))
    constraints = list(
        dict.fromkeys(
            constraints
            + _normalize_optional_constraints(raw_values)
            + _normalize_extra_context_constraint(
                raw_values, max_input_chars=max_input_chars
            )
        )
    )

    goals = list(cast(list[DevelopmentDomain], raw_values.get("goals", [])))
    return NormalizedWidgetInput(
        plz=str(raw_values.get("plz", "")),
        radius_km=float(raw_values.get("radius_km", 0.0)),
        date_value=cast(date, raw_values.get("date")),
        start_time=cast(time, raw_values.get("start_time")),
        available_minutes=int(raw_values.get("available_minutes", 0)),
        effort=cast(Literal["niedrig", "mittel", "hoch"], raw_values.get("effort")),
        budget_eur_max=float(raw_values.get("budget_eur_max", 0.0)),
        child_age_years=float(raw_values.get("child_age_years", 0.0)),
        topics=list(cast(list[str], raw_values.get("topics", []))),
        location_preference=_normalize_location_preference(raw_values, mode=mode),
        goals=goals if goals else [DevelopmentDomain.language],
        constraints=constraints,
        available_materials=list(
            cast(list[str], raw_values.get("available_materials", []))
        ),
    )


def _build_criteria_from_widget_state(
    *, namespace: CriteriaNamespace
) -> ActivitySearchCriteria:
    raw_values = _collect_widget_raw_values(namespace)
    normalized = normalize_widget_input(
        raw_values,
        mode=namespace,
        max_input_chars=int(st.session_state.get("cfg_max_input_chars", 4000)),
    )

    return ActivitySearchCriteria(
        plz=normalized.plz,
        radius_km=normalized.radius_km,
        date=normalized.date_value,
        time_window=TimeWindow(
            start=normalized.start_time,
            end=(
                datetime.combine(normalized.date_value, normalized.start_time)
                + timedelta(minutes=normalized.available_minutes)
            ).time(),
        ),
        effort=normalized.effort,
        budget_eur_max=normalized.budget_eur_max,
        child_age_years=normalized.child_age_years,
        topics=normalized.topics,
        location_preference=normalized.location_preference,
        goals=normalized.goals,
        constraints=normalized.constraints,
        available_materials=normalized.available_materials,
    )


def _render_criteria_validation_error(exc: ValidationError, *, lang: Language) -> None:
    st.sidebar.error(
        _t(
            lang,
            "Bitte prüfe die Eingaben. Details siehe unten.",
            "Please review your inputs. Details are listed below.",
        )
    )
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", []))
        st.sidebar.write(f"- `{loc}`: {err.get('msg', 'invalid')}")


def _criteria_sidebar(
    cfg: AppConfig,
) -> tuple[Optional[ActivitySearchCriteria], Language, FamilyProfile]:
    # Developer navigation: Sidebar is a UI adapter.
    # It initializes adapter keys once from criteria and writes changes back to criteria.
    criteria = get_criteria_state(cfg, key=CRITERIA_DAILY_KEY)
    _ensure_ui_adapter_state(namespace="daily", criteria=criteria)

    st.sidebar.header("Suche")
    lang: Language = cast(Language, st.session_state.get("lang", "DE"))

    on_change_kwargs = {"namespace": "daily", "state_key": CRITERIA_DAILY_KEY}
    formatters = {
        "effort": lambda value: effort_label(value, lang),
        "topics": lambda value: theme_label(value, lang),
        "goals": lambda goal: DOMAIN_LABELS[cast(DevelopmentDomain, goal)],
        "available_materials": _material_label,
    }

    # Group 1 (location/time): top fields stay visible.
    render_filter_fields(
        _core_specs_by_id("date"),
        namespace=CriteriaKeySpace("daily").session_prefix,
        mode="sidebar",
        lang=lang,
        on_change_handler=_sync_widget_change_to_criteria,
        on_change_kwargs=on_change_kwargs,
        container=st.sidebar,
        formatters=formatters,
    )

    age_band_labels = [label for label, _ in AGE_BAND_OPTIONS]
    age_band_map = dict(AGE_BAND_OPTIONS)
    current_age = float(st.session_state.get("profile_child_age_years", 2.5))
    current_band = min(AGE_BAND_OPTIONS, key=lambda item: abs(item[1] - current_age))[0]
    selected_age_band = st.sidebar.selectbox(
        _t(
            lang,
            "Altersband",
            "Age band",
        ),
        options=age_band_labels,
        index=age_band_labels.index(current_band),
        key="profile_child_age_band",
    )
    child_age_years = age_band_map[selected_age_band]
    st.session_state["profile_child_age_years"] = float(child_age_years)
    st.session_state[CriteriaKeySpace("daily").widget("child_age_years")] = float(
        child_age_years
    )

    render_filter_fields(
        _core_specs_by_id("plz", "radius_km"),
        namespace=CriteriaKeySpace("daily").session_prefix,
        mode="sidebar",
        lang=lang,
        on_change_handler=_sync_widget_change_to_criteria,
        on_change_kwargs=on_change_kwargs,
        container=st.sidebar,
        formatters=formatters,
    )

    render_filter_fields(
        _core_specs_by_id("start_time", "available_minutes"),
        namespace=CriteriaKeySpace("daily").session_prefix,
        mode="sidebar",
        lang=lang,
        on_change_handler=_sync_widget_change_to_criteria,
        on_change_kwargs=on_change_kwargs,
        container=st.sidebar,
        formatters=formatters,
    )
    st.sidebar.segmented_control(
        _t(lang, "Ort", "Location"),
        options=["mixed", "outdoor", "indoor"],
        format_func=lambda opt: {
            "mixed": "Gemischt" if lang == "DE" else "Mixed",
            "outdoor": "Draußen" if lang == "DE" else "Outdoor",
            "indoor": "Drinnen" if lang == "DE" else "Indoor",
        }[opt],
        key=CriteriaKeySpace("daily").widget("location_preference"),
        on_change=_sync_widget_change_to_criteria,
        kwargs=on_change_kwargs,
    )

    # Group 2 (constraints and advanced options).
    with st.sidebar.expander(
        _t(
            lang,
            "Rahmenbedingungen erweitern",
            "Expand constraints",
        ),
        expanded=False,
    ):
        render_filter_fields(
            _core_specs_by_id(
                "effort",
                "goals",
                "budget_eur_max",
                "topics",
                "constraints",
                "available_materials",
            ),
            namespace=CriteriaKeySpace("daily").session_prefix,
            mode="sidebar",
            lang=lang,
            on_change_handler=_sync_widget_change_to_criteria,
            on_change_kwargs=on_change_kwargs,
            formatters=formatters,
        )

    # Hidden settings (requested: do not show weather/AI toggles).
    st.session_state["use_weather"] = bool(st.session_state.get("use_weather", True))
    st.session_state["use_ai"] = bool(st.session_state.get("use_ai", cfg.enable_llm))

    # Group 4 (profile/mode/language).

    with st.sidebar.expander(
        _t(lang, "Weitere Profileinstellungen", "Additional profile settings"),
        expanded=False,
    ):
        st.text_input(
            _t(lang, "Name des Kindes", "Name of child"),
            value=st.session_state.get("profile_child_name", "Carla"),
            key="profile_child_name",
        )
        st.text_input(
            _t(lang, "Name der Eltern", "Parent name(s)"),
            value=st.session_state.get("profile_parent_names", "Miri"),
            key="profile_parent_names",
        )
        st.selectbox(
            _t(lang, "Sprache", "Language"),
            options=["DE"],
            index=0,
            key="lang",
        )
        st.text_input(
            _t(
                lang,
                "Weitere Rahmenbedingungen (optional, max 80)",
                "Additional constraints (optional, max 80)",
            ),
            key=CriteriaKeySpace("daily").widget("constraints_optional"),
            max_chars=80,
        )
        st.text_area(
            _t(lang, "Zusätzlicher Kontext", "Additional context"),
            key=CriteriaKeySpace("daily").widget("extra_context"),
            help=_t(
                lang,
                f"Wird auf {cfg.max_input_chars} Zeichen begrenzt.",
                f"Will be limited to {cfg.max_input_chars} characters.",
            ),
        )
        st.toggle(
            _t(
                lang,
                "Offline-Modus (ohne LLM)",
                "Offline mode (without LLM)",
            ),
            value=st.session_state.get("offline_mode", False),
            key="offline_mode",
        )

    child_name = (
        str(st.session_state.get("profile_child_name", "Carla")).strip() or "Carla"
    )
    parent_names = (
        str(st.session_state.get("profile_parent_names", "Miri")).strip() or "Miri"
    )
    lang = cast(Language, st.session_state.get("lang", "DE"))

    family_profile = FamilyProfile(
        child_name=child_name,
        parent_names=parent_names,
        child_age_years=float(child_age_years),
    )

    try:
        criteria = _build_criteria_from_widget_state(namespace="daily")
        st.session_state[CRITERIA_DAILY_KEY] = criteria
        return criteria, lang, family_profile
    except ValidationError as exc:
        _render_criteria_validation_error(exc, lang=lang)
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
            "Die Plan-Erstellung ist gerade fehlgeschlagen. Wir zeigen eine sichere Fallback-Version an.",
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


def _split_markdown_sections(markdown: str) -> dict[str, str]:
    section_map: dict[str, str] = {
        "plan": "",
        "supports": "",
        "sicherheit": "",
        "impulse": "",
        "varianten": "",
    }
    heading_map = {
        "## Plan": "plan",
        "## Was das fördert": "supports",
        "## Sicherheit": "sicherheit",
        "## Eltern-Kind-Impulse": "impulse",
        "## Varianten": "varianten",
    }
    current_key: Optional[str] = None
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped in heading_map:
            current_key = heading_map[stripped]
            continue
        if stripped.startswith("# "):
            continue
        if current_key is None:
            continue
        section_map[current_key] += f"{line}\n"
    return {key: value.strip() for key, value in section_map.items()}


def render_daily_plan_sections(markdown: str, lang: Language) -> None:
    sections = _split_markdown_sections(markdown)

    if sections["plan"]:
        st.markdown("## " + _t(lang, "Plan", ""))
        st.markdown(sections["plan"])

    if sections["supports"]:
        st.markdown("## " + _t(lang, "Was das fördert", ""))
        st.markdown(sections["supports"])

    if sections["sicherheit"]:
        with st.expander(_t(lang, "Sicherheit", ""), expanded=False):
            st.markdown(sections["sicherheit"])

    if sections["impulse"]:
        with st.expander(_t(lang, "Eltern-Kind-Impulse", ""), expanded=False):
            st.markdown(sections["impulse"])

    if sections["varianten"]:
        with st.expander(_t(lang, "Varianten", ""), expanded=False):
            st.markdown(sections["varianten"])


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
        key="daily_export_json",
    )
    st.download_button(
        label=_t(lang, "Markdown herunterladen", ""),
        data=markdown,
        file_name=f"mikroabenteuer-{criteria.date.isoformat()}.md",
        mime="text/markdown",
        key="daily_export_md",
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
        key="daily_export_ics",
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
        send_email = st.checkbox(
            "E-Mail senden", value=False, key="daily_job_send_email"
        )
        create_calendar_event = st.checkbox(
            "Kalendereintrag erstellen",
            value=False,
            key="daily_job_create_calendar_event",
        )
        if st.button("Daily-Job jetzt ausführen", key="daily_job_run_once"):
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
            from mikroabenteuer.openai_activity_service import suggest_activities

            event_weather: EventWeatherSummary | None = None
            if weather is not None:
                resolved_location = _resolve_location_from_plz(criteria.plz)
                if resolved_location is not None:
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
                        country_code=resolved_location["country_code"],
                        city=resolved_location["city"],
                        region=resolved_location["region"],
                        timezone=self.cfg.timezone,
                        data_source="open-meteo",
                    )
                else:
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
                        data_source="open-meteo",
                    )

            result = suggest_activities(
                criteria,
                mode="genau" if mode == "genau" else "schnell",
                base_url=os.getenv("OPENAI_BASE_URL") or None,
                timeout_s=self.cfg.timeout_s,
                max_input_chars=self.cfg.max_input_chars,
                max_output_tokens=self.cfg.max_output_tokens,
                model_fast=self.cfg.openai_model_events_fast,
                model_accurate=self.cfg.openai_model_events_accurate,
                weather=event_weather,
            )
            return {
                "suggestions": list(getattr(result, "suggestions", [])),
                "sources": list(getattr(result, "sources", [])),
                "warnings": list(getattr(result, "warnings_de_en", [])),
                "errors": list(getattr(result, "errors_de_en", [])),
                "error_code": getattr(result, "error_code", None),
                "error_hint": getattr(result, "error_hint_de_en", None),
            }
        except Exception:
            return {
                "suggestions": [],
                "sources": [],
                "warnings": [
                    "Die OpenAI-Suche konnte nicht gestartet werden. / OpenAI search could not be started."
                ],
                "errors": [],
                "error_code": ERROR_CODE_API_NON_RETRYABLE,
                "error_hint": (
                    "Interner Aufruffehler in der Eventsuche. Bitte später erneut versuchen. "
                    "/ Internal invocation error in event search. Please try again later."
                ),
            }


def _extract_validation_failure_details(warnings: list[str]) -> list[str]:
    details: list[str] = []
    for warning in warnings:
        if not warning.startswith(VALIDATION_DETAIL_PREFIX):
            continue
        detail = warning[len(VALIDATION_DETAIL_PREFIX) :].strip()
        if detail:
            details.append(detail)
    return details


def _format_validation_failure_hint(details: list[str]) -> str | None:
    if not details:
        return None
    top_detail = details[0]
    return (
        f"Feldtyp-Fehler: {top_detail}. Retry nur sinnvoll nach Eingabe-/Filteranpassung. "
        f"/ Field type failure: {top_detail}. Retry is mainly useful after adjusting inputs/filters."
    )


def _event_error_message_for_code(error_code: str | None) -> str | None:
    messages = {
        ERROR_CODE_MISSING_API_KEY: (
            "OpenAI API-Key fehlt – Live-Eventsuche ist deaktiviert. "
            "/ OpenAI API key is missing – live event search is disabled."
        ),
        ERROR_CODE_RETRYABLE_UPSTREAM: (
            "Rate Limit oder Serverproblem erkannt, bitte in 1 Minute erneut versuchen. "
            "/ Rate limit or upstream server issue detected, please retry in 1 minute."
        ),
        ERROR_CODE_STRUCTURED_OUTPUT: (
            "Antwort konnte nicht zuverlässig validiert werden; bitte Suche erneut starten. "
            "/ Response validation failed; please run the search again."
        ),
        ERROR_CODE_API_NON_RETRYABLE: (
            "Nicht-retrybarer API-Fehler – bitte Eingaben/Konfiguration prüfen. "
            "/ Non-retryable API error – please review inputs/configuration."
        ),
    }
    if error_code is None:
        return None
    return messages.get(error_code)


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
                    "Offline-Modus aktiv: Ergebnisse stammen aus data/activity_library.json."
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
                    "warnings": ["Session-Limit für API-Anfragen erreicht."],
                    "errors": [],
                }
            else:
                event_result = self.openai_service.search_events(
                    criteria, weather, mode
                )
        event_error_code = cast(Optional[str], event_result.get("error_code"))
        event_error_hint = cast(Optional[str], event_result.get("error_hint"))

        warnings.extend(cast(list[str], event_result.get("warnings", [])))
        warnings.extend(cast(list[str], event_result.get("errors", [])))

        validation_details = _extract_validation_failure_details(
            cast(list[str], event_result.get("warnings", []))
        )
        validation_hint = _format_validation_failure_hint(validation_details)

        class_warning = _event_error_message_for_code(event_error_code)
        if class_warning:
            warnings.append(f"Eventsuche [{event_error_code}]: {class_warning}")
        if event_error_hint:
            warnings.append(f"Technischer Hinweis / Technical hint: {event_error_hint}")
        if validation_hint:
            warnings.append(validation_hint)

        if on_status:
            on_status("Suche abgeschlossen")

        return {
            "weather": weather,
            "warnings": list(dict.fromkeys(warnings)),
            "events": event_result.get("suggestions", []),
            "sources": event_result.get("sources", []),
            "error_code": event_error_code,
            "error_hint": event_error_hint,
        }


@st.cache_resource(show_spinner=False)
def _get_activity_orchestrator(
    cfg: AppConfig,
) -> tuple[OpenAIActivityService, ActivityOrchestrator]:
    openai_service = OpenAIActivityService(cfg=cfg)
    return openai_service, ActivityOrchestrator(cfg=cfg, openai_service=openai_service)


def render_wetter_und_events_section(
    cfg: AppConfig, lang: Language
) -> Optional[dict[str, Any]]:
    # Formular-Adapter folgt einer Einweg-Regel.
    # Interaktion schreibt nach criteria; Rendering liest nur für die Erstinitialisierung.
    criteria = get_criteria_state(cfg, key=CRITERIA_EVENTS_KEY)
    _ensure_ui_adapter_state(namespace="events", criteria=criteria)

    with st.sidebar.form("weather_events_form", clear_on_submit=False):
        st.markdown("### " + _t(lang, "Wetter & Veranstaltungen", ""))
        formatters = {
            "effort": lambda value: effort_label(value, lang),
            "topics": lambda value: theme_label(value, lang),
            "goals": lambda goal: DOMAIN_LABELS[cast(DevelopmentDomain, goal)],
            "available_materials": _material_label,
        }
        render_filter_fields(
            _core_specs_by_id(
                "plz",
                "date",
                "start_time",
                "available_minutes",
                "radius_km",
                "effort",
                "budget_eur_max",
                "topics",
            ),
            namespace=CriteriaKeySpace("events").session_prefix,
            mode="events",
            lang=lang,
            formatters=formatters,
        )
        st.toggle(
            _t(lang, "Ort: draußen bevorzugen", "Prefer outdoor"),
            key=CriteriaKeySpace("events").widget("pref_outdoor"),
            value=st.session_state.get(
                CriteriaKeySpace("events").widget("location_preference"), "mixed"
            )
            == "outdoor",
        )
        st.toggle(
            _t(lang, "Ort: drinnen bevorzugen", "Prefer indoor"),
            key=CriteriaKeySpace("events").widget("pref_indoor"),
            value=st.session_state.get(
                CriteriaKeySpace("events").widget("location_preference"), "mixed"
            )
            == "indoor",
        )
        render_filter_fields(
            _core_specs_by_id("goals", "constraints", "available_materials"),
            namespace=CriteriaKeySpace("events").session_prefix,
            mode="events",
            lang=lang,
            formatters=formatters,
        )
        st.text_input(
            _t(
                lang,
                "Weitere Rahmenbedingungen (optional, max 80)",
                "",
            ),
            key=CriteriaKeySpace("events").widget("constraints_optional"),
            max_chars=80,
        )
        st.text_area(
            _t(
                lang,
                "Zusätzlicher Kontext",
                "",
            ),
            key=CriteriaKeySpace("events").widget("extra_context"),
            help=_t(
                lang,
                f"Wird auf {cfg.max_input_chars} Zeichen begrenzt.",
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

        normalized_preview = normalize_widget_input(
            _collect_widget_raw_values("events"),
            mode="events",
            max_input_chars=cfg.max_input_chars,
        )
        st.session_state[CriteriaKeySpace("events").widget("location_preference")] = (
            normalized_preview.location_preference
        )

        extra_context_raw = str(
            st.session_state.get(CriteriaKeySpace("events").widget("extra_context"), "")
        )
        if len(extra_context_raw) > cfg.max_input_chars:
            st.warning(
                _t(
                    lang,
                    f"Zusätzlicher Kontext wird bei Anfrage auf {cfg.max_input_chars} Zeichen gekürzt.",
                    f"Additional context will be truncated to {cfg.max_input_chars} characters for the request.",
                )
            )

        submitted = st.form_submit_button(
            _t(lang, "Wetter und Veranstaltungen laden", "")
        )

    if submitted:
        try:
            _sync_widget_change_to_criteria(
                namespace="events",
                state_key=CRITERIA_EVENTS_KEY,
                raise_on_error=True,
            )
            st.session_state["weather_events_submitted"] = True
            st.session_state["events_mode"] = mode
            st.rerun()
        except ValidationError as exc:
            _render_criteria_validation_error(exc, lang=lang)
            return None

    def _events_fingerprint(
        criteria_state: ActivitySearchCriteria, mode_value: str
    ) -> str:
        payload = {
            "criteria": criteria_state.model_dump(mode="json"),
            "mode": mode_value,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    criteria = get_criteria_state(cfg, key=CRITERIA_EVENTS_KEY)
    requested_mode = str(st.session_state.get("events_mode", mode))
    needs_refresh = bool(st.session_state.pop("weather_events_submitted", False))

    if needs_refresh:
        _service, orchestrator = _get_activity_orchestrator(cfg)
        status_box = st.sidebar.empty()

        def _status_update(message: str) -> None:
            status_box.info(message)

        run_payload = orchestrator.run(
            criteria, mode=requested_mode, on_status=_status_update
        )
        st.session_state["events_payload"] = run_payload
        st.session_state["events_fingerprint"] = _events_fingerprint(
            criteria, requested_mode
        )
        status_box.success(_t(lang, "Fertig.", ""))

    payload_any = st.session_state.get("events_payload")
    payload = cast(Optional[dict[str, Any]], payload_any)

    if payload is not None:
        actions_left, actions_right = st.sidebar.columns(2)
        with actions_left:
            if st.button(
                _t(lang, "Neu suchen", ""),
                key="events_refresh_button",
            ):
                try:
                    _sync_widget_change_to_criteria(
                        namespace="events",
                        state_key=CRITERIA_EVENTS_KEY,
                        raise_on_error=True,
                    )
                    st.session_state["events_mode"] = mode
                    st.session_state["weather_events_submitted"] = True
                    st.rerun()
                except ValidationError as exc:
                    st.sidebar.error(
                        _t(
                            lang,
                            "Bitte prüfe die Eingaben. Details siehe unten.",
                            "",
                        )
                    )
                    for err in exc.errors():
                        loc = ".".join(str(p) for p in err.get("loc", []))
                        st.sidebar.write(f"- `{loc}`: {err.get('msg', 'invalid')}")

        with actions_right:
            if st.button(
                _t(
                    lang,
                    "Ergebnisse löschen",
                    "",
                ),
                key="events_clear_button",
            ):
                st.session_state.pop("events_payload", None)
                st.session_state.pop("events_fingerprint", None)
                st.rerun()

        st.session_state["events_fingerprint"] = _events_fingerprint(
            criteria, requested_mode
        )

    export_payload_any = st.session_state.get("events_payload")
    export_payload = cast(Optional[dict[str, Any]], export_payload_any)
    if export_payload is not None:
        with st.sidebar:
            st.markdown("### " + _t(lang, "Export", ""))
            st.download_button(
                label=_t(lang, "JSON herunterladen", ""),
                data=json.dumps(
                    export_payload, ensure_ascii=False, indent=2, default=str
                ),
                file_name=f"wetter-events-{criteria.date.isoformat()}.json",
                mime="application/json",
                key="events_export_json",
            )
            st.download_button(
                label=_t(lang, "Markdown herunterladen", ""),
                data=_events_payload_to_markdown(export_payload, lang),
                file_name=f"wetter-events-{criteria.date.isoformat()}.md",
                mime="text/markdown",
                key="events_export_md",
            )

    return payload


def _events_payload_to_markdown(payload: dict[str, Any], lang: Language) -> str:
    lines = ["# Wetter & Veranstaltungen", ""]
    weather = payload.get("weather")
    if weather:
        tags = ", ".join(getattr(weather, "derived_tags", []))
        lines.extend([f"## {_t(lang, 'Wetter', '')}", f"- Tags: {tags}", ""])

    warnings = payload.get("warnings", [])
    if warnings:
        lines.append(f"## {_t(lang, 'Hinweise', '')}")
        lines.extend([f"- {warning}" for warning in warnings])
        lines.append("")

    lines.append(f"## {_t(lang, 'Veranstaltungen', '')}")
    events = payload.get("events", [])
    if not events:
        lines.append("- Aktuell keine Treffer bei Veranstaltungen.")
    for event in events:
        title = str(getattr(event, "title", _t(lang, "Vorschlag", "")))
        reason = str(getattr(event, "reason_de_en", ""))
        lines.append(f"- {title}: {reason}")
    lines.append("")

    sources = payload.get("sources", [])
    if sources:
        lines.append(f"## {_t(lang, 'Quellen', '')}")
        lines.extend([f"- {source}" for source in sources])
    return "\n".join(lines).strip() + "\n"


def render_events_results(payload: Optional[dict[str, Any]], lang: Language) -> None:
    if not payload:
        return

    weather = payload.get("weather")
    if weather:
        st.subheader(_t(lang, "Wetter", ""))
        st.write(f"Tags: {', '.join(weather.derived_tags)}")

    warnings = payload.get("warnings", [])
    if warnings:
        st.subheader(_t(lang, "Hinweise", ""))
        for warning in warnings:
            st.warning(str(warning))

    st.subheader(_t(lang, "Veranstaltungen", ""))
    events = payload.get("events", [])
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
        st.subheader(_t(lang, "Quellen", ""))
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

    criteria = criteria.model_copy(
        update={"child_age_years": float(family_profile.child_age_years)}
    )
    st.session_state[CRITERIA_DAILY_KEY] = criteria

    picked, _candidates = pick_daily_adventure(adventures, criteria, weather)
    picked = _profiled_adventure(picked, family_profile)

    st.subheader(_t(lang, "Abenteuer des Tages", ""))
    st.subheader(picked.title)
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
    render_daily_plan_sections(daily_md, lang)

    st.markdown("#### " + _t(lang, "Plan melden", ""))
    report_reason = st.selectbox(
        _t(lang, "Grund", ""),
        options=REPORT_REASONS,
        key="plan_report_reason",
    )
    if st.button(_t(lang, "Diesen Plan melden", "")):
        report = save_plan_report(activity_plan, report_reason)
        st.success(
            _t(
                lang,
                f"Meldung gespeichert ({report.timestamp_utc}). Keine Personenangaben wurden gespeichert.",
                "",
            )
        )

    with st.expander(
        _t(lang, "Gemeldete Pläne ansehen", ""),
        expanded=False,
    ):
        reports = load_plan_reports(limit=100)
        if reports:
            st.dataframe(reports, width="stretch", hide_index=True)
        else:
            st.caption(_t(lang, "Noch keine Meldungen vorhanden.", ""))

    st.divider()
    events_payload = render_wetter_und_events_section(cfg, lang)

    render_events_results(
        cast(
            Optional[dict[str, Any]],
            st.session_state.get("events_payload") or events_payload,
        ),
        lang,
    )

    with st.sidebar:
        st.markdown("### " + _t(lang, "Export", ""))
        _render_export_block(picked, criteria, weather, daily_md, lang)
        _render_automation_block(cfg, criteria, lang)

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
