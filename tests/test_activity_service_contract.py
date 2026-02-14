from __future__ import annotations

import json
from datetime import date, time

from src.mikroabenteuer.models import (
    ActivitySearchCriteria,
    ActivitySuggestionResult,
    IndoorOutdoor,
    TimeWindow,
    WeatherCondition,
    WeatherSummary,
)
from src.mikroabenteuer.openai_activity_service import _build_user_prompt


def test_activity_search_criteria_to_llm_params_contains_expected_fields() -> None:
    criteria = ActivitySearchCriteria(
        plz="40215",
        radius_km=10.0,
        date=date(2026, 1, 20),
        time_window=TimeWindow(start=time(9, 0), end=time(10, 30)),
        effort="mittel",
        budget_eur_max=35.0,
        topics=["natur"],
        available_materials=["pens", "tape"],
        max_suggestions=4,
    )

    params = criteria.to_llm_params()

    assert params["plz"] == "40215"
    assert params["time_start"] == "09:00:00"
    assert params["time_end"] == "10:30:00"
    assert params["available_minutes"] == 90
    assert params["max_suggestions"] == 4
    assert params["available_materials"] == ["pens", "tape"]


def test_openai_activity_prompt_uses_extended_contract_types() -> None:
    criteria = ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 1, 20),
        time_window=TimeWindow(start=time(8, 0), end=time(9, 0)),
        effort="niedrig",
        budget_eur_max=10.0,
        topics=["outdoor"],
    )
    weather = WeatherSummary(
        condition=WeatherCondition.cloudy,
        summary_de_en="Bewölkt / Cloudy",
        country_code="DE",
        city="Düsseldorf",
    )

    prompt = _build_user_prompt(criteria, weather=weather, strategy=None)

    assert "Gib maximal" in prompt
    assert "40215" in prompt
    assert IndoorOutdoor.mixed.value == "mixed"


def test_activity_suggestion_schema_avoids_uri_format_for_openai_strict_mode() -> None:
    schema = ActivitySuggestionResult.model_json_schema()
    schema_text = json.dumps(schema)

    assert '"format": "uri"' not in schema_text
