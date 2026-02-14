from __future__ import annotations

from dataclasses import replace
from datetime import date, time

from src.mikroabenteuer.config import load_config
from src.mikroabenteuer.models import ActivitySearchCriteria, MicroAdventure, TimeWindow
from src.mikroabenteuer.openai_gen import generate_activity_plan


def _criteria() -> ActivitySearchCriteria:
    return ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 2, 14),
        time_window=TimeWindow(start=time(9, 0), end=time(9, 30)),
        effort="mittel",
        budget_eur_max=15.0,
        topics=["natur"],
    )


def _adventure() -> MicroAdventure:
    return MicroAdventure(
        slug="park-mini",
        title="Park-Mini",
        area="Volksgarten",
        short="Kleine Entdeckerrunde",
        duration_minutes=30,
        distance_km=1.0,
        best_time="vormittags",
        stroller_ok=True,
        start_point="Parkeingang",
        route_steps=["Ein Ziel wählen", "Sammeln", "Abschluss"],
        preparation=["Schuhe anziehen"],
        packing_list=["Wasser"],
        execution_tips=["Kurz halten"],
        variations=["Indoor mit Kissen"],
        toddler_benefits=["Sprache"],
        carla_tip="Kind führen lassen",
        risks=["Nasse Wege"],
        mitigations=["Langsam gehen"],
        tags=["outdoor"],
    )


def test_parent_script_mode_is_timeboxed_and_child_led() -> None:
    cfg = replace(load_config(), enable_llm=False, openai_api_key=None)

    plan = generate_activity_plan(
        cfg,
        _adventure(),
        _criteria(),
        weather=None,
        plan_mode="parent_script",
    )

    joined = "\n".join(plan.steps)
    assert "Describe" in joined
    assert "Imitate" in joined
    assert "Praise" in joined
    assert "Active listening" in joined
    assert any("Child-led" in step for step in plan.steps)
    assert any("min" in step for step in plan.steps)
