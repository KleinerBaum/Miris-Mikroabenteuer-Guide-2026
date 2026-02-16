from __future__ import annotations

from datetime import date, time

import pytest
from pydantic import ValidationError

from mikroabenteuer.models import (
    ActivitySearchCriteria,
    DevelopmentDomain,
    TimeWindow,
)


def test_topics_are_normalized_and_deduplicated() -> None:
    criteria = ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 1, 20),
        time_window=TimeWindow(start=time(9, 0), end=time(10, 30)),
        effort="mittel",
        budget_eur_max=20.0,
        topics=[" Natur ", "natur", "KREATIV", ""],
    )

    assert criteria.topics == ["natur", "kreativ"]


def test_time_window_order_is_validated() -> None:
    with pytest.raises(
        ValidationError, match="time_window.end must be after time_window.start"
    ):
        ActivitySearchCriteria(
            plz="40215",
            radius_km=5.0,
            date=date(2026, 1, 20),
            time_window=TimeWindow(start=time(10, 0), end=time(10, 0)),
            effort="mittel",
            budget_eur_max=20.0,
            topics=[],
        )


def test_available_minutes_is_derived_from_time_window() -> None:
    criteria = ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 1, 20),
        time_window=TimeWindow(start=time(9, 30), end=time(11, 0)),
        effort="mittel",
        budget_eur_max=20.0,
        topics=[],
    )

    assert criteria.available_minutes == 90


@pytest.mark.parametrize(
    ("radius_km", "budget_eur_max"),
    [
        (0.5, 0.0),
        (50.0, 250.0),
    ],
)
def test_boundary_values_are_supported(radius_km: float, budget_eur_max: float) -> None:
    criteria = ActivitySearchCriteria(
        plz="40215",
        radius_km=radius_km,
        date=date(2026, 1, 20),
        time_window=TimeWindow(start=time(9, 0), end=time(9, 30)),
        effort="niedrig",
        budget_eur_max=budget_eur_max,
        topics=["outdoor"],
    )

    assert criteria.radius_km == radius_km
    assert criteria.budget_eur_max == budget_eur_max


def test_too_many_topics_raise_validation_error() -> None:
    with pytest.raises(ValidationError, match="topics supports at most 8 entries"):
        ActivitySearchCriteria(
            plz="40215",
            radius_km=5.0,
            date=date(2026, 1, 20),
            time_window=TimeWindow(start=time(9, 0), end=time(10, 0)),
            effort="mittel",
            budget_eur_max=20.0,
            topics=[f"topic-{idx}" for idx in range(9)],
        )


def test_goals_require_one_or_two_domains_and_constraints_are_sanitized() -> None:
    criteria = ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 1, 20),
        time_window=TimeWindow(start=time(9, 0), end=time(10, 0)),
        effort="mittel",
        budget_eur_max=20.0,
        topics=[],
        goals=[
            DevelopmentDomain.language,
            DevelopmentDomain.language,
            DevelopmentDomain.cognitive,
        ],
        constraints=["No screens<script>", "No screens"],
    )

    assert criteria.goals == [DevelopmentDomain.language, DevelopmentDomain.cognitive]
    assert criteria.constraints == ["No screensscript", "No screens"]


def test_more_than_two_goals_raise_validation_error() -> None:
    with pytest.raises(ValidationError, match="goals requires 1-2 domains"):
        ActivitySearchCriteria(
            plz="40215",
            radius_km=5.0,
            date=date(2026, 1, 20),
            time_window=TimeWindow(start=time(9, 0), end=time(10, 0)),
            effort="mittel",
            budget_eur_max=20.0,
            topics=[],
            goals=[
                DevelopmentDomain.language,
                DevelopmentDomain.cognitive,
                DevelopmentDomain.sensory,
            ],
        )
