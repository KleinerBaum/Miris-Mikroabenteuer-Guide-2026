# mikroabenteuer/openai_activity_service.py
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Literal, cast

from pydantic import ValidationError

from .moderation import SAFE_BLOCK_MESSAGE_DE_EN, moderate_text
from .models import (
    ActivitySearchCriteria,
    ActivitySuggestionResult,
    SearchStrategy,
    WeatherSummary,
)

from .openai_settings import (
    configure_openai_api_key,
    resolve_openai_api_key,
)
from .pii_redaction import redact_pii
from .retry import retry_with_backoff


def _truncate_text_with_limit(text: str, *, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _build_system_instructions() -> str:
    # Keep it short; schema enforcement happens via structured outputs.
    return (
        "You are a careful local activity and events researcher. "
        "Use the web_search tool to find real, currently listed events and activities. "
        "Prefer official organizer pages, venue pages, or reputable local listings. "
        "Return results strictly in the provided JSON schema."
    )


def _build_user_prompt(
    criteria: ActivitySearchCriteria,
    weather: WeatherSummary | None,
    strategy: SearchStrategy | None,
) -> str:
    params = criteria.to_llm_params()
    if weather is None:
        weather_payload = None
    elif hasattr(weather, "model_dump"):
        weather_payload = weather.model_dump()
    else:
        weather_payload = asdict(weather)

    weather_block = (
        f"Wetterlage / Weather:\n{weather_payload}\n"
        if weather_payload is not None
        else "Wetterlage / Weather: unknown\n"
    )

    strategy_block = (
        f"Suchstrategie / Search strategy:\n{strategy.model_dump()}\n"
        if strategy is not None
        else "Suchstrategie / Search strategy: neutral\n"
    )

    return redact_pii(
        f"""
Finde passende Mikroabenteuer und Veranstaltungen.

Kriterien / Criteria:
{params}

{weather_block}
{strategy_block}

Regeln / Rules:
- Suche innerhalb von Radius {params["radius_km"]} km um PLZ {params["plz"]}.
- Zieltag: {params["date"]}, Zeitfenster: {params["time_start"]}–{params["time_end"]}.
- Budget: <= {params["budget_eur_max"]} EUR (Obergrenze). Wenn Kosten unbekannt, schätze konservativ oder markiere als unknown.
- Themen (codes): {params["topics"]}.
- Gib maximal {params["max_suggestions"]} Vorschläge.

Output-Anforderungen:
- Für jeden Vorschlag: kurzer Grund (DE/EN in einem String), mindestens 1 Quelle-URL (http/https).
- Wenn du keine Events findest, gib zumindest activity_idea Vorschläge (ohne harte Zeiten) mit Quellen, die die Idee stützen.
""".strip()
    )


def _select_model(mode: Literal["schnell", "genau"]) -> str:
    # As requested: fast= gpt-4o-mini, accurate= o3-mini
    return "gpt-4o-mini" if mode == "schnell" else "o3-mini"


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


def _template_fallback_result(
    weather: WeatherSummary | None,
) -> ActivitySuggestionResult:
    return ActivitySuggestionResult(
        weather=weather,
        suggestions=[],
        sources=[],
        warnings_de_en=[
            "Die Online-Suche war vorübergehend nicht verfügbar. / Online search was temporarily unavailable."
        ],
        errors_de_en=[
            "Wir zeigen aktuell sichere Offline-Vorlagen statt Live-Ergebnissen. / Showing safe curated templates instead of live results."
        ],
    )


def suggest_activities(
    criteria: ActivitySearchCriteria,
    mode: Literal["schnell", "genau"],
    *,
    # Optional: EU endpoint support (e.g. "https://eu.api.openai.com/v1")
    base_url: str | None = None,
    timeout_s: float = 45.0,
    max_input_chars: int = 4000,
    max_output_tokens: int = 800,
    # Use existing retry_with_backoff; keep SDK retries off to avoid double retry.
    sdk_max_retries: int = 0,
    # Orchestrator-provided context (recommended)
    weather: WeatherSummary | None = None,
    strategy: SearchStrategy | None = None,
) -> ActivitySuggestionResult:
    """
    OpenAI Responses API call with web_search tool enabled and strict structured output.

    Returns: ActivitySuggestionResult (Pydantic validated).
    """
    configure_openai_api_key()
    api_key = resolve_openai_api_key()
    if not api_key:
        return _template_fallback_result(weather)

    model = _select_model(mode)

    # OpenAI SDK import is local to keep module import cheap in Streamlit
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return _template_fallback_result(weather)

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,  # None => default (or env OPENAI_BASE_URL)
        timeout=timeout_s,
        max_retries=sdk_max_retries,
    )

    tools: list[dict] = [{"type": "web_search"}]

    # If we have geo context, pass it to web_search for better local results.
    if (
        weather
        and weather.country_code
        and (weather.city or weather.region or weather.timezone)
    ):
        tools = [
            {
                "type": "web_search",
                "user_location": {
                    "type": "approximate",
                    "country": weather.country_code,
                    "city": weather.city or "",
                    "region": weather.region or "",
                    "timezone": weather.timezone or "",
                },
            }
        ]

    sys_msg = redact_pii(_build_system_instructions())
    raw_user_msg = _build_user_prompt(criteria, weather, strategy)
    user_msg, truncated = _truncate_text_with_limit(
        raw_user_msg,
        max_chars=max_input_chars,
    )

    def _call_openai() -> ActivitySuggestionResult:
        if moderate_text(client, text=user_msg, stage="input"):
            return ActivitySuggestionResult(
                weather=weather,
                suggestions=[],
                sources=[],
                warnings_de_en=[],
                errors_de_en=[SAFE_BLOCK_MESSAGE_DE_EN],
            )

        resp = client.responses.parse(
            model=model,
            max_output_tokens=max_output_tokens,
            input=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            tools=cast(Any, tools),
            tool_choice="auto",
            include=["web_search_call.action.sources"],
            text_format=ActivitySuggestionResult,
        )

        parsed: ActivitySuggestionResult | None = getattr(resp, "output_parsed", None)
        if parsed is None:
            raise RuntimeError(
                "No structured output parsed from response (output_parsed is None)."
            )
        if truncated:
            parsed.warnings_de_en.append(
                "Hinweis / Notice: Eingabe wurde gekürzt, um das Sicherheitslimit einzuhalten. / Input was truncated to enforce the safety limit."
            )
        if moderate_text(
            client,
            text=parsed.model_dump_json(indent=2),
            stage="output",
        ):
            return ActivitySuggestionResult(
                weather=weather,
                suggestions=[],
                sources=[],
                warnings_de_en=[],
                errors_de_en=[SAFE_BLOCK_MESSAGE_DE_EN],
            )
        return parsed

    try:
        return retry_with_backoff(
            max_attempts=3,
            base_delay=0.5,
            should_retry=_is_retryable_openai_error,
        )(_call_openai)()
    except ValidationError:
        return _template_fallback_result(weather)
    except Exception as exc:  # noqa: BLE001
        if _is_retryable_openai_error(exc):
            return _template_fallback_result(weather)
        return ActivitySuggestionResult(
            weather=weather,
            suggestions=[],
            sources=[],
            warnings_de_en=[],
            errors_de_en=[
                "Die Eventsuche ist aktuell nicht verfügbar. / Event search is currently unavailable."
            ],
        )
