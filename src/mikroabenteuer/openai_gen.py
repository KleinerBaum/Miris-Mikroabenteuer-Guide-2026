# src/mikroabenteuer/openai_gen.py
from __future__ import annotations

from typing import Any, Literal, Optional, cast

from pydantic import ValidationError

from .config import AppConfig
from .moderation import SAFE_BLOCK_MESSAGE_DE_EN, moderate_text
from .materials import blocked_materials, material_matches_blocklist, substitutions_for
from .models import (
    ActivityPlan,
    ActivityRequest,
    ActivitySearchCriteria,
    AgeUnit,
    DevelopmentDomain,
    IndoorOutdoor,
    MicroAdventure,
)
from .pii_redaction import redact_pii
from .retry import retry_with_backoff
from .weather import WeatherSummary


class ActivityGenerationError(RuntimeError):
    """Raised when structured activity generation fails."""


MIN_RESPONSIVE_PROMPTS = 3
MAX_RESPONSIVE_PROMPTS = 6
PlanMode = Literal["standard", "parent_script"]


def _domain_label(domain: DevelopmentDomain) -> str:
    labels: dict[DevelopmentDomain, str] = {
        DevelopmentDomain.gross_motor: "Grobmotorik / Gross motor",
        DevelopmentDomain.fine_motor: "Feinmotorik / Fine motor",
        DevelopmentDomain.language: "Sprache / Language",
        DevelopmentDomain.social_emotional: "Sozial-emotional / Social-emotional",
        DevelopmentDomain.sensory: "Sensorik / Sensory",
        DevelopmentDomain.cognitive: "Kognition / Cognitive",
    }
    return labels[domain]


def _domain_prompt(domain: DevelopmentDomain) -> str:
    prompts: dict[DevelopmentDomain, str] = {
        DevelopmentDomain.gross_motor: "Welche große Bewegung macht dir gerade am meisten Spaß?",
        DevelopmentDomain.fine_motor: "Kannst du mit deinen Fingern ein kleines Detail zeigen?",
        DevelopmentDomain.language: "Wie würdest du das in deinen eigenen Worten beschreiben?",
        DevelopmentDomain.social_emotional: "Wie fühlt sich dein Körper gerade an und was hilft dir?",
        DevelopmentDomain.sensory: "Welches Geräusch, Gefühl oder Geruch nimmst du gerade wahr?",
        DevelopmentDomain.cognitive: "Was glaubst du passiert als Nächstes und warum?",
    }
    return prompts[domain]


def _responsive_exchange_prompts(goals: list[str]) -> list[str]:
    language_prompt = "Say: Can you teach me one word for this? / Do: Repeat your child's word and add one new word together."
    has_language_goal = any(
        "language" in goal.casefold() or "sprache" in goal.casefold() for goal in goals
    )
    prompts = [
        "Say: I see you looking closely. What did you notice? / Do: Point together and wait for your child's answer.",
        "Say: Great idea, let's try your version next. / Do: Copy your child's action once before offering the next step.",
        language_prompt
        if has_language_goal
        else "Say: Should we do one more round or take a break? / Do: Let your child choose and mirror their pace.",
    ]
    if has_language_goal:
        prompts.append(
            "Say: Should we do one more round or take a break? / Do: Let your child choose and mirror their pace."
        )
    return prompts


def _ensure_responsive_prompts(prompts: list[str], goals: list[str]) -> list[str]:
    """Guarantee 3-6 short say/do prompts that drive responsive exchanges."""
    normalized = [prompt.strip() for prompt in prompts if prompt and prompt.strip()]
    say_do_prompts = [
        prompt
        for prompt in normalized
        if "say:" in prompt.casefold() and "do:" in prompt.casefold()
    ]

    for fallback_prompt in _responsive_exchange_prompts(goals):
        if len(say_do_prompts) >= MIN_RESPONSIVE_PROMPTS:
            break
        if fallback_prompt not in say_do_prompts:
            say_do_prompts.append(fallback_prompt)

    has_language_goal = any(
        "language" in goal.casefold() or "sprache" in goal.casefold() for goal in goals
    )
    language_marker = ("word", "wort", "sprache")
    if has_language_goal and not any(
        any(marker in prompt.casefold() for marker in language_marker)
        for prompt in say_do_prompts
    ):
        language_prompt = _responsive_exchange_prompts(["Sprache / Language"])[2]
        if len(say_do_prompts) >= MAX_RESPONSIVE_PROMPTS:
            say_do_prompts[-1] = language_prompt
        else:
            say_do_prompts.append(language_prompt)

    return say_do_prompts[:MAX_RESPONSIVE_PROMPTS]


def _truncate_text_with_limit(text: str, *, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _is_retryable_openai_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 500, 502, 503, 504}:
        return True
    if status_code is not None:
        return False

    lower_message = str(exc).lower()
    transient_markers = (
        "timeout",
        "timed out",
        "temporar",
        "rate limit",
        "too many requests",
        "service unavailable",
    )
    return any(marker in lower_message for marker in transient_markers)


def _ensure_plan_b_variants(
    plan: ActivityPlan,
    *,
    available_minutes: int,
    start_point: str,
) -> ActivityPlan:
    existing = [
        variant.strip() for variant in plan.variants if variant and variant.strip()
    ]
    categories: dict[str, str] = {
        "lower energy": (
            "Lower energy / Weniger Energie: Halbtempo-Version mit ruhigeren Bewegungen"
            f" und Pausen nach Bedarf ({max(10, available_minutes // 2)}-{available_minutes} min)."
        ),
        "higher energy": (
            "Higher energy / Mehr Energie: Zwei zusätzliche Bewegungsrunden "
            "oder Suchaufgaben mit klaren Stopp-Signalen."
        ),
        "indoor swap": (
            "Indoor swap / Indoor-Tausch: Gleiches Ziel drinnen mit Kissen-Parcours, "
            "Malerkrepp-Linien oder Fenstersuche umsetzen."
        ),
        "no materials": (
            "No materials / Ohne Material: Nur Stimme, Hände und vorhandene Umgebung "
            f"nutzen (z. B. {start_point or 'zu Hause / at home'})."
        ),
    }

    normalized = "\n".join(existing).casefold()
    missing = [text for label, text in categories.items() if label not in normalized]

    return plan.model_copy(update={"variants": [*existing, *missing]})


def _build_activity_request(
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
) -> ActivityRequest:
    age_years = max(0.0, float(criteria.child_age_years))
    indoor_outdoor = IndoorOutdoor.outdoor
    if "indoor" in {t.lower() for t in adventure.tags}:
        indoor_outdoor = IndoorOutdoor.indoor

    return ActivityRequest(
        age_value=age_years,
        age_unit=AgeUnit.years,
        duration_minutes=int(adventure.duration_minutes),
        indoor_outdoor=indoor_outdoor,
        materials=list(adventure.packing_list),
        goals=[_domain_label(goal) for goal in criteria.goals],
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
    supports = [_domain_label(goal) for goal in criteria.goals]
    weather_note = "Weather unavailable"
    if weather:
        weather_note = ", ".join(weather.derived_tags) or "Weather loaded"

    return _ensure_plan_b_variants(
        ActivityPlan(
            title=adventure.title,
            summary=f"{adventure.short} ({weather_note})",
            steps=list(adventure.route_steps),
            safety_notes=list(adventure.mitigations)
            or ["Keep activity short and flexible."],
            parent_child_prompts=_ensure_responsive_prompts(
                [
                    "Say: What do you want to explore first? / Do: Pause and follow your child's choice.",
                    "Say: Can you show me your favorite tiny discovery? / Do: Copy your child's gesture and name it together.",
                    *[_domain_prompt(goal) for goal in criteria.goals],
                ],
                supports,
            ),
            variants=list(adventure.variations)
            + [f"Short version for {criteria.available_minutes} minutes"],
            supports=supports,
        ),
        available_minutes=criteria.available_minutes,
        start_point=adventure.start_point,
    )


def _enforce_material_constraints(
    plan: ActivityPlan,
    criteria: ActivitySearchCriteria,
) -> ActivityPlan:
    blocked = blocked_materials(criteria.available_materials)
    if not blocked:
        return plan

    def _clean(items: list[str]) -> list[str]:
        return [item for item in items if not material_matches_blocklist(item, blocked)]

    safety_notes = list(plan.safety_notes)
    for substitution in substitutions_for(blocked):
        if substitution not in safety_notes:
            safety_notes.append(substitution)

    summary = plan.summary
    if material_matches_blocklist(summary, blocked):
        summary = (
            "Materialangepasste Version ohne nicht verfügbare Gegenstände. "
            "/ Material-adjusted version without unavailable items."
        )

    return plan.model_copy(
        update={
            "summary": summary,
            "steps": _clean(plan.steps),
            "variants": _clean(plan.variants),
            "parent_child_prompts": _clean(plan.parent_child_prompts),
            "safety_notes": safety_notes,
        }
    )


def _safe_fallback_plan(request: ActivityRequest) -> ActivityPlan:
    return _ensure_plan_b_variants(
        ActivityPlan(
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
            parent_child_prompts=_ensure_responsive_prompts(
                [
                    "Say: Welcher Gegenstand fühlt sich am weichsten an? / Do: Lass dein Kind zuerst zeigen und benennen.",
                    "Say: Möchtest du noch eine ruhige Runde machen oder jetzt Pause? / Do: Übernimm die gewählte Option sofort.",
                ],
                list(request.goals),
            ),
            variants=[
                f"Kurzversion: nur 2 Schritte in {max(10, request.duration_minutes // 2)} Minuten",
                "Indoor-Variante: Gegenstände nur in einem Zimmer finden",
            ],
            supports=list(request.goals),
        ),
        available_minutes=request.duration_minutes,
        start_point="zu Hause / at home",
    )


def _apply_parent_script_mode(
    plan: ActivityPlan,
    criteria: ActivitySearchCriteria,
) -> ActivityPlan:
    total_minutes = max(6, min(20, criteria.available_minutes))
    step_minutes = max(1, total_minutes // 5)
    final_minutes = max(1, total_minutes - (step_minutes * 4))
    return _ensure_plan_b_variants(
        ActivityPlan(
            title=f"{plan.title} · Elternskript / Parent script",
            summary=(
                "Kurzes, kindgeführtes 4-Schritte-Skript (Describe, Imitate, Praise, Active listening). "
                "Kaum Vorbereitung, direkt wiederholbar. "
                "/ Short child-led 4-step script (Describe, Imitate, Praise, Active listening). "
                "Minimal prep and easy to repeat."
            ),
            steps=[
                f"{step_minutes} min – Describe: Beschreibe neutral, was dein Kind tut. / Describe what your child is doing without correcting.",
                f"{step_minutes} min – Imitate: Mache die Bewegung oder Idee deines Kindes nach. / Copy your child's action and pace.",
                f"{step_minutes} min – Praise: Lobe konkret ('Du hast ... ausprobiert'). / Give specific praise for effort and choices.",
                f"{step_minutes} min – Active listening: Wiederhole die Worte deines Kindes und warte 5 Sekunden. / Reflect your child's words and pause.",
                f"{final_minutes} min – Child-led repeat: Kind entscheidet, was wiederholt wird oder wie beendet wird. / Child chooses repeat or finish.",
            ],
            safety_notes=list(plan.safety_notes)
            or [
                "Nur sichere, alltägliche Umgebung nutzen. / Use a safe everyday environment.",
            ],
            parent_child_prompts=[
                "Say: Ich sehe, du stapelst die Steine. / I see you stacking the blocks.",
                "Say: Ich mache es wie du. / I will do it your way.",
                "Say: Stark, wie du drangeblieben bist. / Great effort, you kept trying.",
                "Say: Du willst noch einmal? / You want one more round?",
            ],
            variants=[
                "Null-Vorbereitung: Nutze das, was schon da ist (Kissen, Becher, Blätter). / Zero-prep: use what's already there.",
                "Wiederholbar: Dasselbe Skript 1-2x täglich in 6-20 Minuten. / Repeatable: run the same script 1-2x daily in 6-20 minutes.",
            ],
            supports=list(plan.supports),
        ),
        available_minutes=criteria.available_minutes,
        start_point="zu Hause / at home",
    )


def _blocked_activity_plan() -> ActivityPlan:
    return _ensure_plan_b_variants(
        ActivityPlan(
            title="Inhalt blockiert / Content blocked",
            summary=SAFE_BLOCK_MESSAGE_DE_EN,
            steps=[],
            safety_notes=[
                "Bitte Anfrage anpassen und erneut versuchen. / Please revise the prompt and retry."
            ],
            parent_child_prompts=_ensure_responsive_prompts(
                [], ["Sicherheit / Safety"]
            ),
            variants=[],
            supports=["Sicherheit / Safety"],
        ),
        available_minutes=10,
        start_point="zu Hause / at home",
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
        "cutter",
        "saw",
        "drill",
        "messer",
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

    scissors_keywords = {"scissors", "schere"}
    if any(keyword in haystack for keyword in scissors_keywords):
        age_months = _request_age_months(request)
        if age_months < 72:
            child_safe_markers = {
                "safety scissors",
                "child-safe scissors",
                "kinderschere",
            }
            supervision_markers = {
                "under supervision",
                "with supervision",
                "adult supervision",
                "unter aufsicht",
                "mit aufsicht",
            }
            if not (
                any(marker in haystack for marker in child_safe_markers)
                and any(marker in haystack for marker in supervision_markers)
            ):
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

## What this supports / Was das fördert
{chr(10).join([f"- {s}" for s in plan.supports])}

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
    plan_mode: PlanMode = "standard",
) -> ActivityPlan:
    activity_request = _build_activity_request(adventure, criteria)

    if not cfg.enable_llm or not cfg.openai_api_key:
        plan = _fallback_activity_plan(adventure, criteria, weather)
        if not validate_activity_plan(plan, activity_request):
            plan = _safe_fallback_plan(activity_request)
        if plan_mode == "parent_script":
            plan = _apply_parent_script_mode(plan, criteria)
        plan = _enforce_material_constraints(plan, criteria)
        return plan

    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        plan = _fallback_activity_plan(adventure, criteria, weather)
        if not validate_activity_plan(plan, activity_request):
            plan = _safe_fallback_plan(activity_request)
        if plan_mode == "parent_script":
            plan = _apply_parent_script_mode(plan, criteria)
        plan = _enforce_material_constraints(plan, criteria)
        return plan

    client = OpenAI(api_key=cfg.openai_api_key, timeout=cfg.timeout_s)

    payload = {
        "activity_request": activity_request.model_dump(mode="json"),
        "criteria": criteria.model_dump(mode="json"),
        "weather": weather.__dict__ if weather else None,
        "adventure_seed": adventure.__dict__,
    }

    tools = [{"type": "web_search"}] if cfg.enable_web_search else []

    def _call_openai() -> ActivityPlan:
        raw_user_content = redact_pii(
            (
                "Build an ActivityPlan from this ActivityRequest and context. "
                "Steps must be concrete and safe."
                f"\n\nContext:\n{payload}"
            )
        )
        user_content, truncated = _truncate_text_with_limit(
            raw_user_content,
            max_chars=cfg.max_input_chars,
        )
        if moderate_text(client, text=user_content, stage="input"):
            return _blocked_activity_plan()

        resp = client.responses.parse(
            model=cfg.openai_model_plan,
            max_output_tokens=cfg.max_output_tokens,
            input=[
                {
                    "role": "developer",
                    "content": redact_pii(
                        "Create a practical bilingual-ready toddler activity plan. "
                        "Always return valid structured output. "
                        "Include Plan B variants that cover lower energy, higher energy, "
                        "indoor swap, and no materials swap."
                    ),
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            tools=cast(Any, tools),
            text_format=ActivityPlan,
        )
        parsed: ActivityPlan | None = getattr(resp, "output_parsed", None)
        if truncated:
            parsed_summary_prefix = (
                "Hinweis / Notice: Eingabe wurde gekürzt, um das Sicherheitslimit einzuhalten. "
                "/ Input was truncated to enforce the safety limit. "
            )
            if parsed is not None:
                parsed.summary = f"{parsed_summary_prefix}{parsed.summary}"
        if parsed is not None and not parsed.supports:
            parsed.supports = [_domain_label(goal) for goal in criteria.goals]
            parsed.parent_child_prompts = [
                *parsed.parent_child_prompts,
                *[_domain_prompt(goal) for goal in criteria.goals],
            ]
        if parsed is not None:
            parsed.parent_child_prompts = _ensure_responsive_prompts(
                parsed.parent_child_prompts,
                parsed.supports or [_domain_label(goal) for goal in criteria.goals],
            )
            parsed = _ensure_plan_b_variants(
                parsed,
                available_minutes=criteria.available_minutes,
                start_point=adventure.start_point,
            )
        if parsed is None:
            raise ActivityGenerationError(
                "No structured output parsed from response (output_parsed is None)."
            )
        if moderate_text(
            client,
            text=parsed.model_dump_json(indent=2),
            stage="output",
        ):
            return _blocked_activity_plan()
        return parsed

    try:
        plan = retry_with_backoff(
            max_attempts=3,
            base_delay=0.5,
            should_retry=_is_retryable_openai_error,
        )(_call_openai)()
        if not validate_activity_plan(plan, activity_request):
            plan = _safe_fallback_plan(activity_request)
        if plan_mode == "parent_script":
            plan = _apply_parent_script_mode(plan, criteria)
        plan = _enforce_material_constraints(plan, criteria)
        return plan
    except ValidationError:
        plan = _safe_fallback_plan(activity_request)
        if plan_mode == "parent_script":
            plan = _apply_parent_script_mode(plan, criteria)
        plan = _enforce_material_constraints(plan, criteria)
        return plan
    except Exception as exc:  # noqa: BLE001
        if _is_retryable_openai_error(exc):
            plan = _safe_fallback_plan(activity_request)
            if plan_mode == "parent_script":
                plan = _apply_parent_script_mode(plan, criteria)
            plan = _enforce_material_constraints(plan, criteria)
            return plan
        raise ActivityGenerationError(str(exc)) from exc


# Backward compatible wrapper for scheduler/export flows.
def generate_daily_markdown(
    cfg: AppConfig,
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
    plan_mode: PlanMode = "standard",
) -> str:
    plan = generate_activity_plan(
        cfg,
        adventure,
        criteria,
        weather,
        plan_mode=plan_mode,
    )
    return render_activity_plan_markdown(plan)
