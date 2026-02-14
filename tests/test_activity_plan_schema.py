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
    validate_activity_plan,
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

    assert "## Plan" in markdown
    assert "## Sicherheit" in markdown
    assert "## Eltern-Kind-Impulse" in markdown
    assert "## Varianten" in markdown


def test_validate_activity_plan_blocks_small_parts_for_under_three_fixture() -> None:
    request = ActivityRequest(
        age_value=30,
        age_unit=AgeUnit.months,
        duration_minutes=30,
        indoor_outdoor=IndoorOutdoor.indoor,
        materials=["Perlen"],
        goals=["Sortieren"],
    )
    unsafe_plan = ActivityPlan(
        title="Perlen sortieren",
        summary="Kleinteile mit bunten Perlen verwenden.",
        steps=["Lege kleine Perlen in Schalen."],
        safety_notes=["Aufsicht halten."],
        parent_child_prompts=["Welche Perle magst du?"],
        variants=["Mit Murmeln erweitern"],
    )

    assert validate_activity_plan(unsafe_plan, request) is False


def test_validate_activity_plan_blocks_fire_heat_and_chemicals_fixture() -> None:
    request = ActivityRequest(
        age_value=5,
        age_unit=AgeUnit.years,
        duration_minutes=35,
        indoor_outdoor=IndoorOutdoor.outdoor,
        materials=["Wasser"],
        goals=["Beobachtung"],
    )
    unsafe_plan = ActivityPlan(
        title="Lagerfeuer-Experiment",
        summary="Wir nutzen Feuer und Bleichmittel fuer Effekte.",
        steps=["Kerze anzuenden und mit Loesungsmittel arbeiten."],
        safety_notes=["Vorsicht"],
        parent_child_prompts=["Siehst du die Flamme?"],
        variants=["Mit Grill"],
    )

    assert validate_activity_plan(unsafe_plan, request) is False


def test_generate_activity_plan_returns_safe_fallback_when_fallback_is_unsafe() -> None:
    cfg = replace(load_config(), enable_llm=False, openai_api_key=None)
    unsafe_adventure = replace(
        _build_micro_adventure(),
        age_min=2.0,
        age_max=2.5,
        route_steps=["Spiele mit kleinen Perlen auf dem Tisch."],
    )

    plan = generate_activity_plan(
        cfg,
        unsafe_adventure,
        _build_criteria(),
        weather=None,
    )

    assert "Safe fallback plan" in plan.title
    assert all("Perlen" not in step for step in plan.steps)
