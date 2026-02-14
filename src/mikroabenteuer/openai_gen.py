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


def render_activity_plan_markdown(plan: ActivityPlan) -> str:
    return f"""# Mikroabenteuer des Tages 🌿

**{plan.title}**  
{plan.summary}

## Plan (kurz & klar)
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
    if not cfg.enable_llm or not cfg.openai_api_key:
        return _fallback_activity_plan(adventure, criteria, weather)

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return _fallback_activity_plan(adventure, criteria, weather)

    client = OpenAI(api_key=cfg.openai_api_key)

    activity_request = _build_activity_request(adventure, criteria)
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
        return retry_with_backoff(max_attempts=3, base_delay=0.5)(_call_openai)()
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
