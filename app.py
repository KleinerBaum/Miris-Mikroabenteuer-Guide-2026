# ruff: noqa: E402
from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

import streamlit as st
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mikroabenteuer.config import AppConfig, load_config
from src.mikroabenteuer.constants import (
    Language,
    effort_label,
    theme_label,
    theme_options,
)
from src.mikroabenteuer.data_seed import seed_adventures
from src.mikroabenteuer.email_templates import render_daily_email_html
from src.mikroabenteuer.ics import build_ics_event
from src.mikroabenteuer.models import ActivitySearchCriteria, MicroAdventure
from src.mikroabenteuer.openai_gen import generate_daily_markdown
from src.mikroabenteuer.recommender import filter_adventures, pick_daily_adventure
from src.mikroabenteuer.scheduler import run_daily_job_once
from src.mikroabenteuer.weather import WeatherSummary, fetch_weather_for_day


st.set_page_config(page_title="Mikroabenteuer mit Carla", page_icon="🌿", layout="wide")


def _t(lang: Language, de: str, en: str) -> str:
    return de if lang == "DE" else en


def inject_custom_styles(background_path: Path) -> None:
    if not background_path.exists():
        return

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
            h1, h2, h3, .stCaption, p, label {{ color: #1f2937 !important; }}
            .stDownloadButton button,
            .stButton button {{
                background-color: #1f2937 !important;
                color: #f9fafb !important;
                border: 1px solid #111827 !important;
            }}
            .stDownloadButton button:hover,
            .stButton button:hover {{
                background-color: #111827 !important;
                color: #ffffff !important;
            }}
            .stDownloadButton button:disabled {{
                background-color: #e5e7eb !important;
                color: #374151 !important;
                border-color: #d1d5db !important;
            }}
            .stExpander [data-testid="stExpanderToggleIcon"],
            .stExpander summary p,
            .stExpander summary span {{
                color: #f3f4f6 !important;
            }}
            .stExpander div[data-testid="stExpanderDetails"] pre,
            .stExpander div[data-testid="stExpanderDetails"] code,
            .stExpander div[data-testid="stExpanderDetails"] span {{
                color: #f9fafb !important;
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


def _criteria_sidebar(
    cfg: AppConfig,
) -> tuple[Optional[ActivitySearchCriteria], Language]:
    st.sidebar.header("Suche / Search")
    lang: Language = st.sidebar.selectbox(
        "Sprache / Language", options=["DE", "EN"], index=0
    )

    day_val = st.sidebar.date_input(
        _t(lang, "Datum / Date", "Date / Datum"), value=date.today()
    )

    raw: dict[str, Any] = {
        "postal_code": st.sidebar.text_input(
            _t(lang, "PLZ / Postal code", "Postal code / PLZ"),
            value=cfg.default_postal_code,
            help=_t(
                lang,
                "5-stellige deutsche PLZ (z. B. 40215).",
                "5-digit German postal code (e.g. 40215).",
            ),
        ),
        "radius_km": st.sidebar.slider(
            "Radius (km)",
            min_value=0.5,
            max_value=50.0,
            step=0.5,
            value=float(cfg.default_radius_km),
        ),
        "day": day_val,
        "available_minutes": st.sidebar.number_input(
            _t(lang, "Verfügbare Zeit (Minuten)", "Available time (minutes)"),
            min_value=15,
            max_value=360,
            value=int(cfg.default_available_minutes),
            step=5,
        ),
        "effort": st.sidebar.selectbox(
            _t(lang, "Aufwand / Effort", "Effort / Aufwand"),
            options=["niedrig", "mittel", "hoch"],
            index=["niedrig", "mittel", "hoch"].index(
                cfg.default_effort
                if cfg.default_effort in {"niedrig", "mittel", "hoch"}
                else "mittel"
            ),
            format_func=lambda x: effort_label(x, lang),
        ),
        "budget_eur_max": st.sidebar.number_input(
            _t(lang, "Budget (max €)", "Budget (max €)"),
            min_value=0.0,
            max_value=250.0,
            value=float(cfg.default_budget_eur),
            step=1.0,
        ),
        "themes": st.sidebar.multiselect(
            _t(lang, "Themen / Themes", "Themes / Themen"),
            options=theme_options(lang),
            default=[],
            format_func=lambda x: theme_label(x, lang),
        ),
        "start_time": None,
        "end_time": None,
    }

    st.session_state["use_weather"] = st.sidebar.toggle(
        _t(lang, "Wetter berücksichtigen", "Use weather"), value=True
    )
    st.session_state["use_ai"] = st.sidebar.toggle(
        _t(lang, "KI-Text (OpenAI) nutzen", "Use AI text (OpenAI)"),
        value=cfg.enable_llm,
    )

    try:
        return ActivitySearchCriteria(**raw), lang
    except ValidationError as exc:
        st.sidebar.error(_t(lang, "Ungültige Eingaben:", "Invalid inputs:"))
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []))
            st.sidebar.write(f"- `{loc}`: {err.get('msg', 'invalid')}")
        return None, lang


def _generate_markdown_with_retry(
    cfg: AppConfig,
    picked: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
    lang: Language,
) -> str:
    attempts = 3
    wait_s = 1.0
    last_err: Optional[Exception] = None

    cfg_payload = {**cfg.__dict__}
    if not st.session_state.get("use_ai", False):
        cfg_payload["enable_llm"] = False
    cfg_runtime = cfg.__class__(**cfg_payload)

    for _ in range(attempts):
        try:
            return generate_daily_markdown(cfg_runtime, picked, criteria, weather)
        except Exception as exc:  # defensive wrapper for UI resilience
            last_err = exc
            time.sleep(wait_s)
            wait_s *= 2

    st.warning(
        _t(
            lang,
            "KI-Erstellung fehlgeschlagen. Es wird eine Fallback-Version angezeigt.",
            "AI generation failed. A fallback version is shown.",
        )
    )
    if last_err:
        st.caption(str(last_err))
    return generate_daily_markdown(cfg_runtime, picked, criteria, weather)


def _render_adventure_details(a: MicroAdventure, lang: Language) -> None:
    st.markdown(f"**{a.title}**  \n{a.short}")
    cols = st.columns(4)
    cols[0].metric(_t(lang, "Dauer", "Duration"), f"{a.duration_minutes} min")
    cols[1].metric(_t(lang, "Distanz", "Distance"), f"{a.distance_km:.1f} km")
    cols[2].metric(_t(lang, "Kinderwagen", "Stroller"), "✅" if a.stroller_ok else "—")
    cols[3].metric(_t(lang, "Sicherheit", "Safety"), a.safety_level)

    st.markdown("### " + _t(lang, "Startpunkt", "Start point"))
    st.write(a.start_point)

    st.markdown("### " + _t(lang, "Ablauf", "Steps"))
    for step in a.route_steps:
        st.write(f"- {step}")


def _render_export_block(
    picked: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
    markdown: str,
    lang: Language,
) -> None:
    st.subheader(_t(lang, "Export", "Export"))
    json_payload = {
        "criteria": criteria.model_dump(mode="json"),
        "weather": weather.__dict__ if weather else None,
        "adventure": picked.__dict__,
        "markdown": markdown,
    }
    st.download_button(
        label=_t(lang, "JSON herunterladen", "Download JSON"),
        data=json.dumps(json_payload, ensure_ascii=False, indent=2, default=str),
        file_name=f"mikroabenteuer-{criteria.day.isoformat()}.json",
        mime="application/json",
    )
    st.download_button(
        label=_t(lang, "Markdown herunterladen", "Download Markdown"),
        data=markdown,
        file_name=f"mikroabenteuer-{criteria.day.isoformat()}.md",
        mime="text/markdown",
    )

    ics_bytes = build_ics_event(
        day=criteria.day,
        summary=f"Mikroabenteuer: {picked.title}",
        description=markdown,
        location=picked.area,
        tzid="Europe/Berlin",
        start_time_local=criteria.start_time,
        duration_minutes=picked.duration_minutes,
    )
    st.download_button(
        label="ICS herunterladen / Download ICS",
        data=ics_bytes,
        file_name="mikroabenteuer.ics",
        mime="text/calendar",
    )

    email_html = render_daily_email_html(
        picked, criteria, criteria.day, markdown, weather
    )
    with st.expander(_t(lang, "E-Mail Vorschau", "Email preview"), expanded=False):
        st.code(
            email_html[:3000] + ("..." if len(email_html) > 3000 else ""),
            language="html",
        )


def _render_automation_block(
    cfg: AppConfig, criteria: ActivitySearchCriteria, lang: Language
) -> None:
    with st.expander(
        _t(lang, "Automation (optional)", "Automation (optional)"), expanded=False
    ):
        send_email = st.checkbox("E-Mail senden / Send email", value=False)
        create_calendar_event = st.checkbox(
            "Kalendereintrag erstellen / Create calendar event", value=False
        )
        if st.button("Daily-Job jetzt ausführen / Run daily job now"):
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
                        f"Automation fehlgeschlagen: {exc}",
                        f"Automation failed: {exc}",
                    )
                )


def main() -> None:
    cfg = load_config()
    inject_custom_styles(ROOT / "Hintergrund.png")

    st.title("Mikroabenteuer mit Carla / Micro-adventures with Carla")
    top_col_left, top_col_center, top_col_right = st.columns([1, 1.6, 1])
    with top_col_center:
        st.image(image="20251219_155329.jpg", width=240)

    criteria, lang = _criteria_sidebar(cfg)
    adventures = _load_adventures()

    if criteria is None:
        st.warning(_t(lang, "Bitte Eingaben korrigieren.", "Please fix the inputs."))
        st.stop()

    weather: Optional[WeatherSummary] = None
    if st.session_state.get("use_weather", True):
        weather = _get_weather(criteria.day.isoformat(), cfg.timezone)

    picked, _candidates = pick_daily_adventure(adventures, criteria, weather)

    st.subheader(_t(lang, "Abenteuer des Tages", "Daily adventure"))
    if weather:
        st.caption(
            _t(
                lang,
                f"Wetter-Tags: {', '.join(weather.derived_tags)}",
                f"Weather tags: {', '.join(weather.derived_tags)}",
            )
        )

    daily_md = _generate_markdown_with_retry(cfg, picked, criteria, weather, lang)
    st.markdown(daily_md)

    _render_export_block(picked, criteria, weather, daily_md, lang)
    _render_automation_block(cfg, criteria, lang)

    st.divider()
    st.subheader(_t(lang, "Bibliothek", "Library"))
    filtered = filter_adventures(adventures, criteria)
    st.caption(
        _t(
            lang,
            f"{len(filtered)} passende Abenteuer (von {len(adventures)}).",
            f"{len(filtered)} matching adventures (of {len(adventures)}).",
        )
    )
    st.dataframe(
        [a.summary_row() for a in filtered], width="stretch", hide_index=True
    )

    for a in filtered:
        with st.expander(
            f"{a.title} · {a.area} · {a.duration_minutes} min", expanded=False
        ):
            _render_adventure_details(a, lang)

    if os.getenv("ENABLE_DAILY_SCHEDULER", "0") == "1":
        st.info(
            _t(
                lang,
                "Hinweis: Geplanter Scheduler bitte in separatem Prozess via start_scheduler_0820 nutzen.",
                "Hint: Run scheduled jobs in a separate process via start_scheduler_0820.",
            )
        )


if __name__ == "__main__":
    main()
