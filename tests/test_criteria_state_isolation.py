from __future__ import annotations

from dataclasses import replace
from datetime import date, time
import importlib.util
from pathlib import Path
import sys

import pytest

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

REQUIRED_CORE_FIELDS: set[str] = {
    "plz",
    "radius_km",
    "date",
    "start_time",
    "available_minutes",
    "effort",
    "budget_eur_max",
    "topics",
    "goals",
    "constraints",
    "available_materials",
}


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
        namespace="daily",
        state_key=app.CRITERIA_DAILY_KEY,
        raise_on_error=True,
    )
    app._sync_widget_change_to_criteria(
        namespace="events",
        state_key=app.CRITERIA_EVENTS_KEY,
        raise_on_error=True,
    )

    daily = app.st.session_state[app.CRITERIA_DAILY_KEY]
    events = app.st.session_state[app.CRITERIA_EVENTS_KEY]

    assert daily.plz == "40215"
    assert events.plz == "50667"


def test_master_filter_contract_matches_catalog_and_namespaces(monkeypatch) -> None:
    """Schützt Master-Filtervertrag zwischen Daily und Events."""
    common_catalog_fields = {spec.id for spec in app.CORE_FILTER_SPECS}
    supported_criteria_fields = set(app.CRITERIA_WIDGET_FIELDS)

    assert REQUIRED_CORE_FIELDS.issubset(common_catalog_fields)
    assert REQUIRED_CORE_FIELDS.issubset(supported_criteria_fields)
    assert common_catalog_fields.issubset(supported_criteria_fields)

    monkeypatch.setattr(app.st, "session_state", {})
    cfg = replace(load_config(), default_postal_code="40215")
    daily = app.get_criteria_state(cfg, key=app.CRITERIA_DAILY_KEY)
    events = app.get_criteria_state(cfg, key=app.CRITERIA_EVENTS_KEY)

    app._ensure_ui_adapter_state(namespace="daily", criteria=daily)
    app._ensure_ui_adapter_state(namespace="events", criteria=events)

    for field in REQUIRED_CORE_FIELDS:
        assert app.CriteriaKeySpace("daily").widget(field) in app.st.session_state
        assert app.CriteriaKeySpace("events").widget(field) in app.st.session_state


def test_normalize_widget_input_events_merges_special_constraints() -> None:
    raw_values: dict[str, object] = {
        "plz": "50667",
        "radius_km": 8.0,
        "date": date(2026, 2, 14),
        "start_time": time(10, 0),
        "available_minutes": 90,
        "effort": "mittel",
        "budget_eur_max": 30.0,
        "child_age_years": 4.5,
        "topics": ["natur"],
        "location_preference": "mixed",
        "goals": [],
        "constraints": ["Kein Auto"],
        "available_materials": ["paper"],
        "pref_outdoor": True,
        "pref_indoor": False,
        "constraints_optional": "Reizarm, Barrierearm",
        "extra_context": "A" * 30,
    }

    normalized = app.normalize_widget_input(
        raw_values,
        mode="events",
        max_input_chars=10,
    )

    assert normalized.location_preference == "outdoor"
    assert normalized.goals == [DevelopmentDomain.language]
    assert normalized.constraints == [
        "Kein Auto",
        "Reizarm",
        "Barrierearm",
        "Kontext: AAAAAAAAAA",
    ]


def test_build_criteria_from_widget_state_uses_normalized_location_for_events(
    monkeypatch,
) -> None:
    session_state: dict[str, object] = {
        **_seed_widget_state("form", plz="50667"),
        "cfg_max_input_chars": 100,
        "form_pref_outdoor": False,
        "form_pref_indoor": True,
        "form_constraints_optional": "",
        "form_extra_context": "",
    }
    monkeypatch.setattr(app.st, "session_state", session_state)

    criteria = app._build_criteria_from_widget_state(namespace="events")

    assert criteria.location_preference == "indoor"


@pytest.mark.parametrize(
    ("pref_outdoor", "pref_indoor", "expected"),
    [
        (True, False, "outdoor"),
        (False, True, "indoor"),
        (True, True, "mixed"),
        (False, False, "mixed"),
    ],
)
def test_location_preference_mapping_for_events_is_stable(
    pref_outdoor: bool,
    pref_indoor: bool,
    expected: str,
) -> None:
    raw_values: dict[str, object] = {
        "location_preference": "indoor",
        "pref_outdoor": pref_outdoor,
        "pref_indoor": pref_indoor,
    }

    mapped = app._normalize_location_preference(raw_values, mode="events")

    assert mapped == expected
