# src/mikroabenteuer/openai_gen.py
from __future__ import annotations

from typing import Any, Optional, cast

from pydantic import ValidationError

from .config import AppConfig
from .models import (
    ActivityPlan,
    ActivityRequest,
    ActivitySearchCriteria,
    AgeUnit,
    IndoorOutdoor,
    MicroAdventure,
)
from .retry import retry_with_backoff
from .weather import WeatherSummary


class ActivityGenerationError(RuntimeError):
    """Raised when structured activity generation fails."""


def _build_activity_request(
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
) -> ActivityRequest:
    age_years = max(0.0, float((adventure.age_min + adventure.age_max) / 2.0))
    indoor_outdoor = IndoorOutdoor.outdoor
    if "indoor" in {t.lower() for t in adventure.tags}:
        indoor_outdoor = IndoorOutdoor.indoor

    return ActivityRequest(
        age_value=age_years,
        age_unit=AgeUnit.years,
        duration_minutes=int(adventure.duration_minutes),
        indoor_outdoor=indoor_outdoor,
        materials=list(adventure.packing_list),
        goals=list(adventure.toddler_benefits),
        constraints=[
            f"Budget <= {criteria.budget_eur_max:.2f} EUR",
            f"Time window: {criteria.start_time.isoformat()}–{criteria.end_time.isoformat()}",
            f"Effort: {criteria.effort}",
        ],
    )


def _fallback_activity_plan(
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
) -> ActivityPlan:
    weather_note = "Weather unavailable"
    if weather:
        weather_note = ", ".join(weather.derived_tags) or "Weather loaded"

    return ActivityPlan(
        title=adventure.title,
        summary=f"{adventure.short} ({weather_note})",
        steps=list(adventure.route_steps),
        safety_notes=list(adventure.mitigations)
        or ["Keep activity short and flexible."],
        parent_child_prompts=[
            "What do you want to explore first?",
            "Can you show me your favorite tiny discovery?",
        ],
        variants=list(adventure.variations)
        + [
            f"Short version for {criteria.available_minutes} minutes",
        ],
    )


def _safe_fallback_plan(request: ActivityRequest) -> ActivityPlan:
    return ActivityPlan(
        title="Sicheres Alternativprogramm / Safe fallback plan",
        summary=(
            "Wir zeigen eine sichere, altersgerechte Aktivität ohne riskante Elemente. "
            "/ Showing a safe age-appropriate activity without risky elements."
        ),
        steps=[
            "Gemeinsam 5 ruhige Gegenstände in der Wohnung oder im Garten suchen.",
            "Farben benennen und die Gegenstände in eine sichere Sortier-Reihe legen.",
            "Kurze Bewegungsrunde: langsames Balancieren auf einer Linie am Boden.",
            "Mit Wasser trinken und einer ruhigen Abschlussfrage beenden.",
        ],
        safety_notes=[
            "Nur weiche, große Materialien ohne Kleinteile verwenden.",
            "Keine Hitze, keine Flammen, keine scharfen Werkzeuge, keine Chemikalien.",
            "Aktivität jederzeit abbrechen, wenn Überforderung sichtbar ist.",
        ],
        parent_child_prompts=[
            "Welcher Gegenstand fühlt sich am weichsten an?",
            "Möchtest du noch eine ruhige Runde machen oder jetzt Pause?",
        ],
        variants=[
            f"Kurzversion: nur 2 Schritte in {max(10, request.duration_minutes // 2)} Minuten",
            "Indoor-Variante: Gegenstände nur in einem Zimmer finden",
        ],
    )


def _request_age_months(request: ActivityRequest) -> float:
    if request.age_unit is AgeUnit.months:
        return request.age_value
    return request.age_value * 12.0


def validate_activity_plan(plan: ActivityPlan, request: ActivityRequest) -> bool:
    """Return False when the plan contains hard-blocked safety hazards."""
    text_parts = [
        plan.title,
        plan.summary,
        *plan.steps,
        *plan.safety_notes,
        *plan.parent_child_prompts,
        *plan.variants,
    ]
    haystack = "\n".join(text_parts).casefold()

    always_blocked_keywords = {
        "knife",
        "scissors",
        "cutter",
        "saw",
        "drill",
        "messer",
        "schere",
        "säge",
        "bohrer",
        "fire",
        "campfire",
        "stove",
        "oven",
        "boiling",
        "flame",
        "grill",
        "candle",
        "feuer",
        "lagerfeuer",
        "grillen",
        "kerze",
        "kochend",
        "bleach",
        "ammonia",
        "solvent",
        "pesticide",
        "paint thinner",
        "bleichmittel",
        "ammoniak",
        "lösungsmittel",
        "chemikal",
        "verdünner",
    }
    if any(keyword in haystack for keyword in always_blocked_keywords):
        return False

    if _request_age_months(request) < 36:
        under_three_keywords = {
            "small parts",
            "small part",
            "tiny bead",
            "beads",
            "marble",
            "coin",
            "button battery",
            "kleinteile",
            "kleinteil",
            "perlen",
            "murmel",
            "münze",
            "knopfzelle",
        }
        if any(keyword in haystack for keyword in under_three_keywords):
            return False

    return True


def render_activity_plan_markdown(plan: ActivityPlan) -> str:
    return f"""# Mikroabenteuer des Tages 🌿

**{plan.title}**  
{plan.summary}

## Plan
{chr(10).join([f"- {s}" for s in plan.steps])}

## Sicherheit
{chr(10).join([f"- {s}" for s in plan.safety_notes])}

## Eltern-Kind-Impulse
{chr(10).join([f"- {s}" for s in plan.parent_child_prompts])}

## Varianten
{chr(10).join([f"- {s}" for s in plan.variants])}
"""


def generate_activity_plan(
    cfg: AppConfig,
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
) -> ActivityPlan:
    activity_request = _build_activity_request(adventure, criteria)

    if not cfg.enable_llm or not cfg.openai_api_key:
        plan = _fallback_activity_plan(adventure, criteria, weather)
        if not validate_activity_plan(plan, activity_request):
            return _safe_fallback_plan(activity_request)
        return plan

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        plan = _fallback_activity_plan(adventure, criteria, weather)
        if not validate_activity_plan(plan, activity_request):
            return _safe_fallback_plan(activity_request)
        return plan

    client = OpenAI(api_key=cfg.openai_api_key)

    payload = {
        "activity_request": activity_request.model_dump(mode="json"),
        "criteria": criteria.model_dump(mode="json"),
        "weather": weather.__dict__ if weather else None,
        "adventure_seed": adventure.__dict__,
    }

    tools = [{"type": "web_search"}] if cfg.enable_web_search else []

    def _call_openai() -> ActivityPlan:
        resp = client.responses.parse(
            model=cfg.openai_model,
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Create a practical bilingual-ready toddler activity plan. "
                        "Always return valid structured output."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Build an ActivityPlan from this ActivityRequest and context. "
                        "Steps must be concrete and safe."
                        f"\n\nContext:\n{payload}"
                    ),
                },
            ],
            tools=cast(Any, tools),
            text_format=ActivityPlan,
        )
        parsed: ActivityPlan | None = getattr(resp, "output_parsed", None)
        if parsed is None:
            raise ActivityGenerationError(
                "No structured output parsed from response (output_parsed is None)."
            )
        return parsed

    try:
        plan = retry_with_backoff(max_attempts=3, base_delay=0.5)(_call_openai)()
        if not validate_activity_plan(plan, activity_request):
            return _safe_fallback_plan(activity_request)
        return plan
    except (ValidationError, Exception) as exc:
        raise ActivityGenerationError(str(exc)) from exc


# Backward compatible wrapper for scheduler/export flows.
def generate_daily_markdown(
    cfg: AppConfig,
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
) -> str:
    plan = generate_activity_plan(cfg, adventure, criteria, weather)
    return render_activity_plan_markdown(plan)
