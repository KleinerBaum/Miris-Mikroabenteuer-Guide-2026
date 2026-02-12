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

import streamlit as st
import streamlit.components.v1 as components
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
from src.mikroabenteuer.models import (
    ActivitySearchCriteria,
    TimeWindow,
    WeatherCondition as EventWeatherCondition,
    WeatherSummary as EventWeatherSummary,
    MicroAdventure,
)
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

    available_minutes = st.sidebar.number_input(
        _t(lang, "Verfügbare Zeit (Minuten)", "Available time (minutes)"),
        min_value=15,
        max_value=360,
        value=int(cfg.default_available_minutes),
        step=5,
    )

    raw: dict[str, Any] = {
        "plz": st.sidebar.text_input(
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
        "date": day_val,
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
        "topics": st.sidebar.multiselect(
            _t(lang, "Themen / Themes", "Themes / Themen"),
            options=theme_options(lang),
            default=[],
            format_func=lambda x: theme_label(x, lang),
        ),
        "time_window": {
            "start": time(hour=9, minute=0),
            "end": (
                datetime.combine(date.today(), time(hour=9, minute=0))
                + timedelta(minutes=int(available_minutes))
            ).time(),
        },
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
            time_module.sleep(wait_s)
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
        file_name=f"mikroabenteuer-{criteria.date.isoformat()}.json",
        mime="application/json",
    )
    st.download_button(
        label=_t(lang, "Markdown herunterladen", "Download Markdown"),
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
        label="ICS herunterladen / Download ICS",
        data=ics_bytes,
        file_name="mikroabenteuer.ics",
        mime="text/calendar",
    )

    email_html = render_daily_email_html(
        picked, criteria, criteria.date, markdown, weather
    )
    with st.expander(_t(lang, "E-Mail Vorschau", "Email preview"), expanded=False):
        st.caption(
            _t(
                lang,
                "So sieht die E-Mail im Postfach aus. Den HTML-Code kannst du optional unten aufklappen.",
                "This is how the email looks in the inbox. You can optionally expand the HTML source below.",
            )
        )
        components.html(email_html, height=680, scrolling=True)

        with st.expander(_t(lang, "HTML-Code anzeigen", "Show HTML source")):
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
                    summary_de_en="Wetter lokal geladen / Weather loaded locally",
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
                "warnings": [
                    f"OpenAI-Suche aktuell nicht verfügbar / OpenAI search currently unavailable: {exc}"
                ],
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
            on_status("Wetter wird geladen … / Loading weather …")
        weather: Optional[WeatherSummary] = None
        if st.session_state.get("use_weather", True):
            weather = _get_weather(criteria.date.isoformat(), self.cfg.timezone)

        if on_status:
            on_status("Events werden recherchiert … / Researching events …")
        event_result = self.openai_service.search_events(criteria, weather, mode)
        warnings.extend(event_result.get("warnings", []))
        warnings.extend(event_result.get("errors", []))

        if on_status:
            on_status("Suche abgeschlossen / Search finished")

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
    st.subheader(_t(lang, "Wetter & Events", "Weather & Events"))
    st.caption(
        _t(
            lang,
            "Lokale Vorschläge mit Wetter-Check und Live-Quellen.",
            "Local suggestions with weather check and live sources.",
        )
    )

    with st.form("weather_events_form", clear_on_submit=False):
        top_left, top_right = st.columns(2)
        with top_left:
            plz = st.text_input(
                _t(lang, "PLZ / Postal code", "Postal code / PLZ"),
                value=cfg.default_postal_code,
            )
            target_date = st.date_input(
                _t(lang, "Datum / Date", "Date / Datum"), value=date.today()
            )
            start_time = st.time_input(
                _t(lang, "Startzeit", "Start time"), value=time(hour=9, minute=0)
            )
            available_minutes = st.number_input(
                _t(lang, "Zeitbudget (Minuten)", "Time budget (minutes)"),
                min_value=15,
                max_value=360,
                value=int(cfg.default_available_minutes),
                step=5,
            )
        with top_right:
            radius_km = st.slider(
                _t(lang, "Radius (km)", "Radius (km)"),
                min_value=0.5,
                max_value=50.0,
                step=0.5,
                value=float(cfg.default_radius_km),
            )
            effort = st.selectbox(
                _t(lang, "Aufwand / Effort", "Effort / Aufwand"),
                options=["niedrig", "mittel", "hoch"],
                index=["niedrig", "mittel", "hoch"].index(
                    cfg.default_effort
                    if cfg.default_effort in {"niedrig", "mittel", "hoch"}
                    else "mittel"
                ),
                format_func=lambda x: effort_label(x, lang),
            )
            budget = st.number_input(
                _t(lang, "Budget (max €)", "Budget (max €)"),
                min_value=0.0,
                max_value=250.0,
                value=float(cfg.default_budget_eur),
                step=1.0,
            )
            topics = st.multiselect(
                _t(lang, "Themen / Themes", "Themes / Themen"),
                options=theme_options(lang),
                default=[],
                format_func=lambda x: theme_label(x, lang),
            )

        mode = st.radio(
            _t(lang, "Genauigkeit", "Accuracy"),
            options=["schnell", "genau"],
            format_func=lambda m: _t(lang, "Schnell", "Fast")
            if m == "schnell"
            else _t(lang, "Genau", "Precise"),
            horizontal=True,
        )

        submitted = st.form_submit_button(
            _t(lang, "Wetter und Events laden", "Load weather and events")
        )

    if not submitted:
        return

    try:
        criteria = ActivitySearchCriteria(
            plz=plz,
            radius_km=radius_km,
            date=target_date,
            time_window=TimeWindow(
                start=start_time,
                end=(
                    datetime.combine(target_date, start_time)
                    + timedelta(minutes=int(available_minutes))
                ).time(),
            ),
            effort=cast(Literal["niedrig", "mittel", "hoch"], effort),
            budget_eur_max=float(budget),
            topics=topics,
        )
    except ValidationError as exc:
        st.error(
            _t(
                lang,
                "Bitte prüfe die Eingaben. Details siehe unten.",
                "Please check your inputs. See details below.",
            )
        )
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []))
            st.write(f"- `{loc}`: {err.get('msg', 'invalid')}")
        return

    _service, orchestrator = _get_activity_orchestrator(cfg)
    status_box = st.empty()

    def _status_update(message: str) -> None:
        status_box.info(message)

    payload = orchestrator.run(criteria, mode=mode, on_status=_status_update)
    status_box.success(_t(lang, "Fertig.", "Done."))

    weather = payload.get("weather")
    if weather:
        st.markdown("#### " + _t(lang, "Wetter", "Weather"))
        st.write(
            _t(
                lang,
                f"Tags: {', '.join(weather.derived_tags)}",
                f"Tags: {', '.join(weather.derived_tags)}",
            )
        )

    warnings = payload.get("warnings", [])
    if warnings:
        st.markdown("#### " + _t(lang, "Hinweise", "Warnings"))
        for warning in warnings:
            st.warning(str(warning))

    events = payload.get("events", [])
    st.markdown("#### " + _t(lang, "Events", "Events"))
    if not events:
        st.info(
            _t(
                lang,
                "Aktuell keine Event-Treffer. Bitte Radius/Themen anpassen.",
                "No event matches right now. Please adjust radius/topics.",
            )
        )
    for event in events:
        title = str(getattr(event, "title", _t(lang, "Vorschlag", "Suggestion")))
        reason = str(getattr(event, "reason_de_en", ""))
        st.markdown(f"- **{title}** — {reason}")

    sources = payload.get("sources", [])
    if sources:
        st.markdown("#### " + _t(lang, "Quellen", "Sources"))
        for source in sources:
            st.markdown(f"- {source}")


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
        weather = _get_weather(criteria.date.isoformat(), cfg.timezone)

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
    daily_preview_md, daily_details_md = _split_daily_markdown(daily_md)
    st.markdown(daily_preview_md)
    if daily_details_md:
        with st.expander(
            _t(lang, "Details anzeigen / ausblenden", "Show / hide details"),
            expanded=False,
        ):
            st.markdown(daily_details_md)

    st.divider()
    render_wetter_und_events_section(cfg, lang)

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
    st.dataframe([a.summary_row() for a in filtered], width="stretch", hide_index=True)

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
