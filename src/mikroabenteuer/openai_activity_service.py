# mikroabenteuer/openai_activity_service.py
from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import ValidationError

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
from .retry import retry_with_backoff


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

    return f"""
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


def _select_model(mode: Literal["schnell", "genau"]) -> str:
    # As requested: fast= gpt-4o-mini, accurate= o3-mini
    return "gpt-4o-mini" if mode == "schnell" else "o3-mini"


def suggest_activities(
    criteria: ActivitySearchCriteria,
    mode: Literal["schnell", "genau"],
    *,
    # Optional: EU endpoint support (e.g. "https://eu.api.openai.com/v1")
    base_url: str | None = None,
    timeout_s: float = 45.0,
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
        raise RuntimeError(
            "OPENAI_API_KEY fehlt / missing. "
            "Bitte über configure_openai_api_key/resolve_openai_api_key konfigurieren."
        )

    model = _select_model(mode)

    # OpenAI SDK import is local to keep module import cheap in Streamlit
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Python-SDK fehlt / missing. "
            "Bitte installiere die Abhängigkeiten mit `pip install -r requirements.txt` "
            "im aktiven Python-Environment. "
            "Please install dependencies with `pip install -r requirements.txt` "
            "in the active Python environment."
        ) from exc

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,  # None => default (or env OPENAI_BASE_URL)
        timeout=timeout_s,
        max_retries=sdk_max_retries,
    )

    tools: list[dict] = [{"type": "web_search"}]

    # If we have geo context, pass it to web_search for better local results :contentReference[oaicite:5]{index=5}
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

    sys_msg = _build_system_instructions()
    user_msg = _build_user_prompt(criteria, weather, strategy)

    def _call_openai() -> ActivitySuggestionResult:
        # responses.parse enforces schema via structured outputs :contentReference[oaicite:6]{index=6}
        resp = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            tools=tools,  # enables web search :contentReference[oaicite:7]{index=7}
            tool_choice="auto",
            include=[
                "web_search_call.action.sources"
            ],  # include sources metadata :contentReference[oaicite:8]{index=8}
            text_format=ActivitySuggestionResult,
        )

        parsed: ActivitySuggestionResult | None = getattr(resp, "output_parsed", None)
        if parsed is None:
            raise RuntimeError(
                "No structured output parsed from response (output_parsed is None)."
            )
        return parsed

    try:
        result = retry_with_backoff(max_attempts=3, base_delay=0.5)(_call_openai)()
    except ValidationError as ve:
        # In case your retry_with_backoff does not retry validation errors, surface clearly.
        raise RuntimeError(f"Structured output validation failed: {ve}") from ve

    return result
