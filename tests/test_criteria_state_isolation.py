from __future__ import annotations

from dataclasses import replace
from datetime import date, time
import importlib.util
from pathlib import Path
import sys

from mikroabenteuer.config import load_config
from mikroabenteuer.models import DevelopmentDomain


def _load_app_module():
    app_spec = importlib.util.spec_from_file_location("app", Path("app.py"))
    assert app_spec is not None and app_spec.loader is not None
    app_module = importlib.util.module_from_spec(app_spec)
    sys.modules["app"] = app_module
    app_spec.loader.exec_module(app_module)
    return app_module


app = _load_app_module()


def _seed_widget_state(prefix: str, *, plz: str) -> dict[str, object]:
    return {
        f"{prefix}_plz": plz,
        f"{prefix}_radius_km": 5.0,
        f"{prefix}_date": date(2026, 2, 14),
        f"{prefix}_start_time": time(9, 0),
        f"{prefix}_available_minutes": 60,
        f"{prefix}_effort": "mittel",
        f"{prefix}_budget_eur_max": 20.0,
        f"{prefix}_child_age_years": 4.5,
        f"{prefix}_topics": ["natur"],
        f"{prefix}_location_preference": "mixed",
        f"{prefix}_goals": [DevelopmentDomain.language],
        f"{prefix}_constraints": ["No screens"],
        f"{prefix}_available_materials": ["paper"],
    }


def test_get_criteria_state_initializes_daily_and_events_independently(
    monkeypatch,
) -> None:
    monkeypatch.setattr(app.st, "session_state", {})
    cfg = replace(load_config(), default_postal_code="40215")

    daily = app.get_criteria_state(cfg, key=app.CRITERIA_DAILY_KEY)
    events = app.get_criteria_state(cfg, key=app.CRITERIA_EVENTS_KEY)

    assert app.CRITERIA_DAILY_KEY in app.st.session_state
    assert app.CRITERIA_EVENTS_KEY in app.st.session_state
    assert daily.plz == "40215"
    assert events.plz == "40215"
    assert daily is not events


def test_sync_widget_change_updates_only_target_criteria_key(monkeypatch) -> None:
    session_state: dict[str, object] = {
        **_seed_widget_state("sidebar", plz="40215"),
        **_seed_widget_state("form", plz="50667"),
    }
    monkeypatch.setattr(app.st, "session_state", session_state)

    app._sync_widget_change_to_criteria(
        prefix="sidebar",
        state_key=app.CRITERIA_DAILY_KEY,
        raise_on_error=True,
    )
    app._sync_widget_change_to_criteria(
        prefix="form",
        state_key=app.CRITERIA_EVENTS_KEY,
        raise_on_error=True,
    )

    daily = app.st.session_state[app.CRITERIA_DAILY_KEY]
    events = app.st.session_state[app.CRITERIA_EVENTS_KEY]

    assert daily.plz == "40215"
    assert events.plz == "50667"
