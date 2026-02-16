from __future__ import annotations

import pytest

from src.mikroabenteuer.models import (
    ActivityPlan,
    ActivityRequest,
    AgeUnit,
    IndoorOutdoor,
)
from src.mikroabenteuer.openai_gen import validate_activity_plan


@pytest.fixture
def request_under_three() -> ActivityRequest:
    return ActivityRequest(
        age_value=30,
        age_unit=AgeUnit.months,
        duration_minutes=20,
        indoor_outdoor=IndoorOutdoor.indoor,
        materials=["Papier"],
        goals=["Sensorik"],
    )


@pytest.fixture
def request_preschool() -> ActivityRequest:
    return ActivityRequest(
        age_value=5,
        age_unit=AgeUnit.years,
        duration_minutes=20,
        indoor_outdoor=IndoorOutdoor.indoor,
        materials=["Papier"],
        goals=["Sensorik"],
    )


@pytest.fixture
def baseline_plan() -> ActivityPlan:
    return ActivityPlan(
        title="Farbspiel",
        summary="Wir sortieren sichere, große Gegenstände.",
        steps=["Lege große Bausteine nach Farben."],
        safety_notes=["Nur kindgerechte Materialien verwenden."],
        parent_child_prompts=["Welche Farbe gefällt dir?"],
        variants=["Kurzversion mit zwei Farben."],
    )


def _plan_with_trigger(plan: ActivityPlan, trigger: str) -> ActivityPlan:
    return plan.model_copy(
        update={
            "summary": f"{plan.summary} Trigger: {trigger}.",
            "steps": [*plan.steps, f"Nutze: {trigger}."],
        }
    )


@pytest.mark.parametrize(
    "trigger",
    [
        "knife",
        "candles",
        "campfire",
        "bleach",
        "Messer",
        "Kerze",
        "Lagerfeuer",
        "Bleichmittel",
    ],
)
def test_validator_blocks_core_hazards_across_age_bands(
    baseline_plan: ActivityPlan,
    request_under_three: ActivityRequest,
    request_preschool: ActivityRequest,
    trigger: str,
) -> None:
    unsafe_plan = _plan_with_trigger(baseline_plan, trigger)

    assert validate_activity_plan(unsafe_plan, request_under_three) is False
    assert validate_activity_plan(unsafe_plan, request_preschool) is False


@pytest.mark.parametrize("trigger", ["scissors", "Schere"])
def test_validator_blocks_scissors_without_safety_context_for_younger_children(
    baseline_plan: ActivityPlan,
    request_under_three: ActivityRequest,
    request_preschool: ActivityRequest,
    trigger: str,
) -> None:
    unsafe_plan = _plan_with_trigger(baseline_plan, trigger)

    assert validate_activity_plan(unsafe_plan, request_under_three) is False
    assert validate_activity_plan(unsafe_plan, request_preschool) is False


def test_validator_allows_kinderschere_with_supervision_for_preschool() -> None:
    request_preschool = ActivityRequest(
        age_value=5,
        age_unit=AgeUnit.years,
        duration_minutes=20,
        indoor_outdoor=IndoorOutdoor.indoor,
        materials=["Kinderschere"],
        goals=["Feinmotorik"],
    )
    age_suitable_plan = ActivityPlan(
        title="Schneide-Spiel",
        summary="Nutze eine Kinderschere unter Aufsicht.",
        steps=[
            "Schneide Papierstreifen mit Kinderschere unter Aufsicht.",
        ],
        safety_notes=["Nur mit Kinderschere und unter Aufsicht schneiden."],
        parent_child_prompts=["Zeig mir, wie du sicher schneidest."],
        variants=["Stattdessen reißen, wenn Schneiden zu schwierig ist."],
    )

    assert validate_activity_plan(age_suitable_plan, request_preschool) is True


def test_validator_allows_kinderschere_for_under_six_with_supervision() -> None:
    request_kindergarten = ActivityRequest(
        age_value=4,
        age_unit=AgeUnit.years,
        duration_minutes=20,
        indoor_outdoor=IndoorOutdoor.indoor,
        materials=["Kinderschere"],
        goals=["Feinmotorik"],
    )
    age_specific_plan = ActivityPlan(
        title="Schneide-Spiel",
        summary="Nutze eine Kinderschere unter Aufsicht.",
        steps=["Schneide einfache Formen aus Papier aus."],
        safety_notes=["Nur mit Kinderschere und unter Aufsicht schneiden."],
        parent_child_prompts=["Möchtest du zuerst eine gerade Linie schneiden?"],
        variants=["Formen alternativ reißen."],
    )

    assert validate_activity_plan(age_specific_plan, request_kindergarten) is True


@pytest.mark.parametrize(
    "trigger",
    ["small beads", "tiny bead", "Perlen", "Murmel", "Knopfzelle"],
)
def test_validator_blocks_under_three_choking_triggers(
    baseline_plan: ActivityPlan,
    request_under_three: ActivityRequest,
    trigger: str,
) -> None:
    unsafe_plan = _plan_with_trigger(baseline_plan, trigger)

    assert validate_activity_plan(unsafe_plan, request_under_three) is False


def test_validator_allows_age_specific_trigger_for_older_children(
    baseline_plan: ActivityPlan,
    request_preschool: ActivityRequest,
) -> None:
    age_specific_plan = _plan_with_trigger(baseline_plan, "small beads")

    assert validate_activity_plan(age_specific_plan, request_preschool) is True
