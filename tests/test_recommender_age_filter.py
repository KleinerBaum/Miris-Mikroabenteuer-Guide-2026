from __future__ import annotations

from datetime import date, time

from src.mikroabenteuer.models import ActivitySearchCriteria, MicroAdventure, TimeWindow
from src.mikroabenteuer.recommender import filter_adventures


def _criteria(*, child_age_years: float) -> ActivitySearchCriteria:
    return ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 2, 14),
        time_window=TimeWindow(start=time(9, 0), end=time(10, 0)),
        effort="mittel",
        budget_eur_max=20.0,
        child_age_years=child_age_years,
        topics=[],
    )


def _adventure(slug: str, *, age_min: float, age_max: float) -> MicroAdventure:
    return MicroAdventure(
        slug=slug,
        title=slug,
        area="Volksgarten",
        short="Kurz",
        duration_minutes=45,
        distance_km=1.0,
        best_time="vormittags",
        stroller_ok=True,
        start_point="Start",
        route_steps=["Los"],
        preparation=["Wetter"],
        packing_list=["Wasser"],
        execution_tips=["Pausen"],
        variations=["Kurz"],
        toddler_benefits=["Motorik"],
        carla_tip="Tipp",
        risks=["Rutschig"],
        mitigations=["Langsam"],
        tags=["outdoor"],
        age_min=age_min,
        age_max=age_max,
    )


def test_filter_adventures_excludes_age_mismatches() -> None:
    criteria = _criteria(child_age_years=4.0)
    adventures = [
        _adventure("too_young", age_min=0.0, age_max=3.0),
        _adventure("fit", age_min=3.0, age_max=5.0),
        _adventure("too_old", age_min=5.0, age_max=8.0),
    ]

    filtered = filter_adventures(adventures, criteria)

    assert [adventure.slug for adventure in filtered] == ["fit"]
