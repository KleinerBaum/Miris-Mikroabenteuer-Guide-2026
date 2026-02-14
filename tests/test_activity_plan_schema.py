from __future__ import annotations

from datetime import date, time

from dataclasses import replace

from src.mikroabenteuer.config import load_config
from src.mikroabenteuer.models import (
    ActivityPlan,
    ActivityRequest,
    ActivitySearchCriteria,
    AgeUnit,
    IndoorOutdoor,
    MicroAdventure,
    TimeWindow,
)
from src.mikroabenteuer.openai_gen import (
    generate_activity_plan,
    render_activity_plan_markdown,
)


def _build_micro_adventure() -> MicroAdventure:
    return MicroAdventure(
        slug="wald-mini",
        title="Wald-Mini",
        area="Volksgarten",
        short="Kurzer Entdeckerweg",
        duration_minutes=45,
        distance_km=1.2,
        best_time="vormittags",
        stroller_ok=True,
        start_point="Parkeingang",
        route_steps=["Losgehen", "Steine sammeln"],
        preparation=["Wetter prüfen"],
        packing_list=["Wasser", "Snack"],
        execution_tips=["Pausen einplanen"],
        variations=["Indoor-Malrunde"],
        toddler_benefits=["Motorik", "Neugier"],
        carla_tip="Kurz halten",
        risks=["Nasse Wege"],
        mitigations=["Feste Schuhe"],
        tags=["outdoor"],
    )


def _build_criteria() -> ActivitySearchCriteria:
    return ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 2, 14),
        time_window=TimeWindow(start=time(9, 0), end=time(10, 0)),
        effort="mittel",
        budget_eur_max=20.0,
        topics=["natur"],
    )


def test_activity_request_schema_supports_age_unit_and_constraints() -> None:
    request = ActivityRequest(
        age_value=30,
        age_unit=AgeUnit.months,
        duration_minutes=40,
        indoor_outdoor=IndoorOutdoor.mixed,
        materials=["Kreide"],
        goals=["Feinmotorik"],
        constraints=["No screens"],
    )

    assert request.age_unit.value == "months"
    assert request.constraints == ["No screens"]


def test_generate_activity_plan_returns_structured_fallback_when_llm_disabled() -> None:
    cfg = replace(load_config(), enable_llm=False, openai_api_key=None)

    plan = generate_activity_plan(
        cfg,
        _build_micro_adventure(),
        _build_criteria(),
        weather=None,
    )

    assert isinstance(plan, ActivityPlan)
    assert plan.steps
    assert plan.safety_notes
    assert plan.parent_child_prompts


def test_render_activity_plan_markdown_contains_required_sections() -> None:
    plan = ActivityPlan(
        title="Plan-Titel",
        summary="Kurzbeschreibung",
        steps=["Schritt 1"],
        safety_notes=["Hinweis"],
        parent_child_prompts=["Frage"],
        variants=["Variante"],
    )

    markdown = render_activity_plan_markdown(plan)

    assert "## Plan (kurz & klar)" in markdown
    assert "## Sicherheit" in markdown
    assert "## Eltern-Kind-Impulse" in markdown
    assert "## Varianten" in markdown
