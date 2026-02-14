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


def test_offline_selection_returns_top_3_grounded_library_matches() -> None:
    criteria = _criteria().model_copy(
        update={
            "time_window": TimeWindow(start=time(9, 0), end=time(11, 0)),
            "constraints": ["material:helm", "material:wasserflasche"],
        }
    )

    suggestions, warnings = suggest_activities_offline(criteria, child_age_years=8.0)

    assert not warnings
    assert len(suggestions) == 3

    expected_top_titles = [
        "Mini-Radroute / Mini Bike Loop",
        "Natur-Bingo im Park / Nature Bingo in the Park",
        "Markt-Mathe-Rallye / Market Math Hunt",
    ]
    assert [suggestion.title for suggestion in suggestions] == expected_top_titles
    assert all('"library_id":' in suggestion.reason_de_en for suggestion in suggestions)


def test_offline_selection_filters_out_age_and_duration_mismatches() -> None:
    criteria = _criteria().model_copy(
        update={
            "time_window": TimeWindow(start=time(9, 0), end=time(9, 30)),
            "max_suggestions": 5,
        }
    )

    suggestions, warnings = suggest_activities_offline(criteria, child_age_years=11.0)

    assert not suggestions
    assert warnings


def test_offline_selection_respects_unchecked_materials() -> None:
    criteria = _criteria().model_copy(
        update={
            "time_window": TimeWindow(start=time(9, 0), end=time(11, 0)),
            "available_materials": [
                "pens",
                "tape",
                "scissors",
                "bowls",
                "rice",
                "flashlight",
            ],
            "max_suggestions": 5,
        }
    )

    suggestions, _warnings = suggest_activities_offline(criteria, child_age_years=7.0)

    assert suggestions
    assert all("Papier" not in suggestion.reason_de_en for suggestion in suggestions)


def test_offline_selection_returns_substitutions_for_missing_items() -> None:
    criteria = _criteria().model_copy(
        update={
            "available_materials": [
                "pens",
                "tape",
                "scissors",
                "bowls",
                "rice",
                "flashlight",
            ],
        }
    )

    _suggestions, warnings = suggest_activities_offline(criteria, child_age_years=7.0)

    assert any(
        "statt Papier" in warning or "instead of paper" in warning
        for warning in warnings
    )
