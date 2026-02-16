from __future__ import annotations

from datetime import date, time

import pytest
from pydantic import ValidationError

from mikroabenteuer.models import ActivitySearchCriteria, TimeWindow


def test_activity_search_criteria_rejects_invalid_plz() -> None:
    with pytest.raises(ValidationError):
        ActivitySearchCriteria(
            plz="40A15",
            date=date(2026, 1, 1),
            time_window=TimeWindow(start=time(10, 0), end=time(11, 30)),
        )


def test_available_minutes_is_calculated_from_time_window() -> None:
    criteria = ActivitySearchCriteria(
        date=date(2026, 1, 1),
        time_window=TimeWindow(start=time(10, 15), end=time(11, 45)),
    )

    assert criteria.available_minutes == 90
