from __future__ import annotations

from datetime import date, time

from src.mikroabenteuer.activity_library import (
    load_activity_library,
    suggest_activities_offline,
)
from src.mikroabenteuer.models import ActivitySearchCriteria, TimeWindow


def _criteria() -> ActivitySearchCriteria:
    return ActivitySearchCriteria(
        plz="40215",
        radius_km=8.0,
        date=date(2026, 2, 1),
        time_window=TimeWindow(start=time(9, 0), end=time(10, 30)),
        effort="mittel",
        budget_eur_max=20.0,
        topics=["nature", "movement"],
        location_preference="outdoor",
        max_suggestions=3,
    )


def test_activity_library_loads_and_contains_vetted_tags() -> None:
    items = load_activity_library()

    assert items
    assert all(item.domain_tags for item in items)
    assert all(item.materials for item in items)
    assert all(item.safety_notes for item in items)


def test_offline_suggestions_return_results_without_llm() -> None:
    suggestions, warnings = suggest_activities_offline(_criteria(), child_age_years=7.0)

    assert suggestions
    assert not warnings
    assert all("Offline-Bibliothek Treffer" in s.reason_de_en for s in suggestions)
