from __future__ import annotations

from datetime import date, time
from typing import Literal

from src.mikroabenteuer.models import ActivitySearchCriteria, MicroAdventure, TimeWindow
from src.mikroabenteuer.recommender import (
    filter_adventures,
    pick_daily_adventure,
    score_adventure,
)


def _build_adventure(
    slug: str,
    *,
    area: str,
    duration_minutes: int,
    energy_level: str = "mittel",
    difficulty: str = "leicht",
) -> MicroAdventure:
    return MicroAdventure(
        slug=slug,
        title=slug.title(),
        area=area,
        short="Kurzbeschreibung",
        duration_minutes=duration_minutes,
        distance_km=1.0,
        best_time="vormittags",
        stroller_ok=True,
        start_point="Start",
        route_steps=["Schritt 1"],
        preparation=["Vorbereiten"],
        packing_list=["Wasser"],
        execution_tips=["Locker bleiben"],
        variations=["Variation"],
        toddler_benefits=["Sprache"],
        carla_tip="Tipp",
        risks=["Nässe"],
        mitigations=["Regenjacke"],
        tags=["Natur"],
        energy_level=energy_level,
        difficulty=difficulty,
    )


def _criteria(
    *, effort: Literal["niedrig", "mittel", "hoch"] = "mittel"
) -> ActivitySearchCriteria:
    return ActivitySearchCriteria(
        date=date(2026, 1, 1),
        time_window=TimeWindow(start=time(10, 0), end=time(11, 0)),
        effort=effort,
    )


def test_filter_adventures_respects_available_minutes_and_effort() -> None:
    criteria = _criteria(effort="niedrig")
    adventures = [
        _build_adventure("passt", area="Park", duration_minutes=45),
        _build_adventure("zu-lang", area="Park", duration_minutes=90),
        _build_adventure(
            "zu-anstrengend",
            area="Park",
            duration_minutes=45,
            energy_level="hoch",
            difficulty="mittel",
        ),
    ]

    filtered = filter_adventures(adventures, criteria)

    assert [adventure.slug for adventure in filtered] == ["passt"]


def test_score_adventure_boosts_volksgarten() -> None:
    criteria = _criteria()
    volksgarten = _build_adventure(
        "volksgarten", area="Volksgarten Düsseldorf", duration_minutes=45
    )
    elsewhere = _build_adventure("rheinwiese", area="Rheinwiese", duration_minutes=45)

    volksgarten_score = score_adventure(volksgarten, criteria, weather=None)
    elsewhere_score = score_adventure(elsewhere, criteria, weather=None)

    assert volksgarten_score > elsewhere_score


def test_pick_daily_adventure_is_deterministic_for_same_input() -> None:
    criteria = _criteria()
    adventures = [
        _build_adventure("eins", area="Volksgarten", duration_minutes=30),
        _build_adventure("zwei", area="Südpark", duration_minutes=40),
        _build_adventure("drei", area="Rheinwiese", duration_minutes=50),
    ]

    picked_a, _ = pick_daily_adventure(adventures, criteria)
    picked_b, _ = pick_daily_adventure(adventures, criteria)

    assert picked_a.slug == picked_b.slug
