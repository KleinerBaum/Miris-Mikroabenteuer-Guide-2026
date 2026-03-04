# mikroabenteuer/openai_activity_service.py
from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Literal, cast

from pydantic import ValidationError

from .moderation import SAFE_BLOCK_MESSAGE_DE_EN, moderate_text
from .models import (
    ActivitySearchCriteria,
    ActivitySuggestionResult,
    SearchStrategy,
    WeatherSummary,
    validate_http_url,
)

from .openai_settings import (
    configure_openai_api_key,
    resolve_openai_api_key,
)
from .pii_redaction import redact_pii
from .retry import retry_with_backoff

ERROR_CODE_MISSING_API_KEY = "missing_api_key"
ERROR_CODE_RETRYABLE_UPSTREAM = "retryable_upstream"
ERROR_CODE_STRUCTURED_OUTPUT = "structured_output_validation"
ERROR_CODE_API_NON_RETRYABLE = "api_non_retryable"
VALIDATION_DETAIL_PREFIX = "Validation detail / Validierungsdetail: "
RECOVERY_MARKER_SCHEMA_REPAIR = (
    "Recovered after schema repair / Nach Schema-Reparatur wiederhergestellt."
)
SUGGESTION_TITLE_FALLBACK = "Aktivität / Activity"
SUGGESTION_REASON_FALLBACK = (
    "Keine Begründung geliefert. / No rationale provided."
)
INDOOR_OUTDOOR_ALLOWED_VALUES = {"indoor", "outdoor", "mixed"}


def _build_schema_repair_prompt(original_prompt: str) -> str:
    return (
        f"{original_prompt}\n\n"
        "JSON-REPARATURHINWEIS / JSON REPAIR NOTICE:\n"
        "Die vorherige Antwort war nicht valide. Antworte jetzt ausschließlich als valides JSON im exakten Zielschema. "
        "Keine Prosa, keine Markdown-Blöcke, keine zusätzlichen Kommentare."
    )


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
- Verfügbare Haushaltsmaterialien / available household materials: {params["available_materials"]}.
- Empfiehl keine nicht verfügbaren Materialien. Wenn nötig, nenne konkrete Ersatzoptionen mit vorhandenen Dingen.
  / Do not recommend unavailable materials. If needed, provide substitutions using available items.
- Gib maximal {params["max_suggestions"]} Vorschläge.

Output-Anforderungen:
- Für jeden Vorschlag: kurzer Grund (DE/EN in einem String), mindestens 1 Quelle-URL (http/https).
- Wenn du keine Events findest, gib zumindest activity_idea Vorschläge (ohne harte Zeiten) mit Quellen, die die Idee stützen.
""".strip()
    )


def _select_model(
    mode: Literal["schnell", "genau"],
    *,
    model_fast: str,
    model_accurate: str,
) -> str:
    return model_fast if mode == "schnell" else model_accurate


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


def _error_hint_for_code(error_code: str) -> str:
    hints = {
        ERROR_CODE_MISSING_API_KEY: (
            "OpenAI API-Schlüssel fehlt. Bitte Konfiguration prüfen. "
            "/ OpenAI API key missing. Please verify configuration."
        ),
        ERROR_CODE_RETRYABLE_UPSTREAM: (
            "Rate-Limit oder temporärer Dienstfehler. Bitte in etwa 1 Minute erneut versuchen. "
            "/ Rate limit or temporary upstream failure. Please retry in about 1 minute."
        ),
        ERROR_CODE_STRUCTURED_OUTPUT: (
            "Antwortformat konnte nicht validiert werden. Bitte erneut versuchen oder Filter anpassen. "
            "/ Structured output could not be validated. Please retry or adjust filters."
        ),
        ERROR_CODE_API_NON_RETRYABLE: (
            "Nicht-retrybarer API-Fehler. Eingaben/Konfiguration prüfen. "
            "/ Non-retryable API error. Please review inputs/configuration."
        ),
    }
    return hints[error_code]


def _extract_raw_result_payload(response: Any) -> dict[str, Any]:
    parsed_payload = getattr(response, "output_parsed", None)
    if parsed_payload is not None:
        if hasattr(parsed_payload, "model_dump"):
            return cast(dict[str, Any], parsed_payload.model_dump(mode="json"))
        if isinstance(parsed_payload, dict):
            return cast(dict[str, Any], parsed_payload)

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        loaded = json.loads(output_text)
        if isinstance(loaded, dict):
            return cast(dict[str, Any], loaded)

    raise RuntimeError("No structured output payload found in response.")


def _normalize_url_list(raw_urls: Any) -> list[str]:
    values: list[str]
    if isinstance(raw_urls, str):
        values = [raw_urls]
    elif isinstance(raw_urls, list):
        values = [item for item in raw_urls if isinstance(item, str)]
    else:
        values = []

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_url in values:
        candidate = (raw_url or "").strip()
        if not candidate:
            continue
        try:
            clean_url = validate_http_url(candidate)
        except ValueError:
            continue
        if clean_url in seen:
            continue
        normalized.append(clean_url)
        seen.add(clean_url)
    return normalized


def _ensure_string_list(raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        return []
    return [
        item.strip() for item in raw_value if isinstance(item, str) and item.strip()
    ]


def _normalize_result_payload(
    payload: dict[str, Any],
    *,
    criteria: ActivitySearchCriteria,
) -> dict[str, Any]:
    normalized = dict(payload)

    raw_suggestions = normalized.get("suggestions")
    suggestions: list[dict[str, Any]] = []
    normalization_warnings: list[str] = []
    if isinstance(raw_suggestions, list):
        for index, raw_item in enumerate(raw_suggestions):
            if not isinstance(raw_item, dict):
                continue
            item = dict(raw_item)
            title = str(item.get("title") or "").strip()
            item["title"] = title or SUGGESTION_TITLE_FALLBACK
            reason_de_en = str(item.get("reason_de_en") or "").strip()
            item["reason_de_en"] = reason_de_en or SUGGESTION_REASON_FALLBACK
            if item.get("date") in {None, ""}:
                item["date"] = criteria.date.isoformat()
            item.setdefault("description", "")
            if item.get("start_time") == "":
                item["start_time"] = None
            if item.get("end_time") == "":
                item["end_time"] = None
            if item.get("location") == "":
                item["location"] = None
            normalized_indoor_outdoor = str(item.get("indoor_outdoor") or "").strip()
            if normalized_indoor_outdoor not in INDOOR_OUTDOOR_ALLOWED_VALUES:
                item["indoor_outdoor"] = "mixed"
            else:
                item["indoor_outdoor"] = normalized_indoor_outdoor
            item["source_urls"] = _normalize_url_list(item.get("source_urls"))
            if not item["source_urls"]:
                normalization_warnings.append(
                    f"Vorschlag #{index + 1} ohne valide Quellen-URL übernommen. / Suggestion #{index + 1} kept without a valid source URL."
                )
            suggestions.append(item)

    normalized["suggestions"] = suggestions
    normalized["sources"] = _normalize_url_list(normalized.get("sources"))
    normalized["warnings_de_en"] = _ensure_string_list(normalized.get("warnings_de_en"))
    normalized["warnings_de_en"].extend(normalization_warnings)
    normalized["errors_de_en"] = _ensure_string_list(normalized.get("errors_de_en"))
    normalized["error_code"] = normalized.get("error_code") or None
    normalized["error_hint_de_en"] = normalized.get("error_hint_de_en") or None
    return normalized


def _extract_text_for_best_effort(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = getattr(response, "output", None)
    if isinstance(output, list):
        for item in output:
            item_data = item if isinstance(item, dict) else None
            if item_data is None and hasattr(item, "model_dump"):
                dumped = item.model_dump(mode="json")
                if isinstance(dumped, dict):
                    item_data = dumped
            if item_data is None:
                continue

            content = item_data.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                block_data = block if isinstance(block, dict) else None
                if block_data is None and hasattr(block, "model_dump"):
                    dumped_block = block.model_dump(mode="json")
                    if isinstance(dumped_block, dict):
                        block_data = dumped_block
                if block_data is None:
                    continue

                text_value = block_data.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    return text_value.strip()

                if isinstance(block_data.get("type"), str) and block_data.get(
                    "type"
                ) in {
                    "output_text",
                    "text",
                }:
                    nested_text = block_data.get("value")
                    if isinstance(nested_text, str) and nested_text.strip():
                        return nested_text.strip()

            text_value = item_data.get("text")
            if isinstance(text_value, str) and text_value.strip():
                return text_value.strip()

            summary = item_data.get("summary")
            if isinstance(summary, list):
                for summary_item in summary:
                    if isinstance(summary_item, dict):
                        summary_text = summary_item.get("text")
                        if isinstance(summary_text, str) and summary_text.strip():
                            return summary_text.strip()
    return ""


def _best_effort_extract_payload(response: Any) -> dict[str, Any] | None:
    candidate_text = _extract_text_for_best_effort(response)
    if not candidate_text:
        return None

    urls = _normalize_url_list(
        re.findall(r"https?://[^\s\]\[\)\(\"']+", candidate_text)
    )
    if not urls:
        return None

    lines = [line.strip() for line in candidate_text.splitlines() if line.strip()]
    title = lines[0] if lines else "Aktivität / Activity"
    if len(title) > 120:
        title = f"{title[:117].rstrip()}..."

    description = " ".join(lines[1:3]).strip() if len(lines) > 1 else candidate_text
    if not description:
        description = "Kurzbeschreibung aus Modellantwort extrahiert. / Summary extracted from model output."
    if len(description) > 300:
        description = f"{description[:297].rstrip()}..."

    return {
        "suggestions": [
            {
                "title": title,
                "description": description,
                "reason_de_en": "Best-effort aus unvollständiger Modellantwort. / Best effort from incomplete model output.",
                "source_urls": urls,
            }
        ],
        "sources": urls,
    }


def _safe_validation_issue_metadata(exc: ValidationError) -> list[str]:
    def _format_loc(loc: Any) -> str:
        if not isinstance(loc, (list, tuple)):
            return "response"
        path = ""
        for part in loc:
            if isinstance(part, int):
                path += f"[{part}]"
            elif isinstance(part, str):
                path = f"{path}.{part}" if path else part
        return path or "response"

    issues: list[str] = []
    seen: set[str] = set()
    for error in exc.errors():
        field_path = _format_loc(error.get("loc"))
        error_type = str(error.get("type") or "unknown")
        issue = f"{field_path} {error_type}"
        if issue in seen:
            continue
        seen.add(issue)
        issues.append(issue)
    return issues


def _build_web_search_user_location(
    weather: WeatherSummary,
) -> dict[str, str] | None:
    country = (weather.country_code or "").strip()
    city = (weather.city or "").strip()
    region = (weather.region or "").strip()
    timezone = (weather.timezone or "").strip()
    if not all((country, city, region, timezone)):
        return None
    return {
        "type": "approximate",
        "country": country,
        "city": city,
        "region": region,
        "timezone": timezone,
    }


def _template_fallback_result(
    weather: WeatherSummary | None,
    *,
    error_code: str,
    warnings_de_en: list[str] | None = None,
    errors_de_en: list[str] | None = None,
) -> ActivitySuggestionResult:
    return ActivitySuggestionResult(
        weather=weather,
        suggestions=[],
        sources=[],
        warnings_de_en=warnings_de_en
        or [
            "Die Online-Suche war vorübergehend nicht verfügbar. / Online search was temporarily unavailable."
        ],
        errors_de_en=errors_de_en
        or [
            "Wir zeigen aktuell sichere Offline-Vorlagen statt Live-Ergebnissen. / Showing safe curated templates instead of live results."
        ],
        error_code=error_code,
        error_hint_de_en=_error_hint_for_code(error_code),
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
    model_fast: str = "gpt-4o-mini",
    model_accurate: str = "o3-mini",
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
        return _template_fallback_result(
            weather,
            error_code=ERROR_CODE_MISSING_API_KEY,
            warnings_de_en=[
                "OpenAI-Zugang ist nicht konfiguriert. / OpenAI access is not configured."
            ],
            errors_de_en=[
                "Live-Eventsuche derzeit deaktiviert, bis ein API-Key verfügbar ist. / Live event search is disabled until an API key is configured."
            ],
        )

    model = _select_model(
        mode,
        model_fast=model_fast,
        model_accurate=model_accurate,
    )

    # OpenAI SDK import is local to keep module import cheap in Streamlit
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return _template_fallback_result(
            weather,
            error_code=ERROR_CODE_API_NON_RETRYABLE,
            warnings_de_en=[
                "OpenAI-SDK nicht verfügbar. / OpenAI SDK is not available."
            ],
            errors_de_en=[
                "Live-Eventsuche kann ohne SDK nicht ausgeführt werden. / Live event search cannot run without the SDK."
            ],
        )

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,  # None => default (or env OPENAI_BASE_URL)
        timeout=timeout_s,
        max_retries=sdk_max_retries,
    )

    tools: list[dict] = [{"type": "web_search"}]

    # If we have complete geo context, pass it to web_search for better local results.
    if weather:
        user_location = _build_web_search_user_location(weather)
        if user_location is not None:
            tools = [{"type": "web_search", "user_location": user_location}]

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

        def _request_and_validate(prompt: str) -> tuple[ActivitySuggestionResult, Any]:
            response = client.responses.parse(
                model=model,
                max_output_tokens=max_output_tokens,
                input=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt},
                ],
                tools=cast(Any, tools),
                tool_choice="auto",
                include=["web_search_call.action.sources"],
                text_format=ActivitySuggestionResult,
            )
            raw_payload = _extract_raw_result_payload(response)
            normalized_payload = _normalize_result_payload(
                raw_payload,
                criteria=criteria,
            )
            return ActivitySuggestionResult.model_validate(normalized_payload), response

        try:
            parsed, _ = _request_and_validate(user_msg)
        except (
            ValidationError,
            RuntimeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            repair_prompt = _build_schema_repair_prompt(user_msg)
            repair_response: Any = None
            try:
                parsed, _ = _request_and_validate(repair_prompt)
                parsed.warnings_de_en.append(RECOVERY_MARKER_SCHEMA_REPAIR)
            except (
                ValidationError,
                RuntimeError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                repair_response = client.responses.create(
                    model=model,
                    max_output_tokens=max_output_tokens,
                    input=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": repair_prompt},
                    ],
                    tools=cast(Any, tools),
                    tool_choice="auto",
                    include=["web_search_call.action.sources"],
                )
                best_effort_payload = _best_effort_extract_payload(repair_response)
                if best_effort_payload is None:
                    return _template_fallback_result(
                        weather,
                        error_code=ERROR_CODE_STRUCTURED_OUTPUT,
                    )
                normalized_best_effort = _normalize_result_payload(
                    best_effort_payload,
                    criteria=criteria,
                )
                parsed = ActivitySuggestionResult.model_validate(normalized_best_effort)
                parsed.warnings_de_en.extend(
                    [
                        RECOVERY_MARKER_SCHEMA_REPAIR,
                        "Best-effort-Extraktion verwendet. / Used best-effort extraction.",
                    ]
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
    except ValidationError as exc:
        safe_issues = _safe_validation_issue_metadata(exc)
        technical_notes = [
            f"{VALIDATION_DETAIL_PREFIX}{issue}" for issue in safe_issues[:3]
        ]
        return _template_fallback_result(
            weather,
            error_code=ERROR_CODE_STRUCTURED_OUTPUT,
            warnings_de_en=[
                "Antwortschema-Validierung fehlgeschlagen. / Response schema validation failed."
            ]
            + technical_notes,
        )
    except Exception as exc:  # noqa: BLE001
        if "No structured output payload found" in str(exc):
            return _template_fallback_result(
                weather,
                error_code=ERROR_CODE_STRUCTURED_OUTPUT,
            )
        if _is_retryable_openai_error(exc):
            return _template_fallback_result(
                weather,
                error_code=ERROR_CODE_RETRYABLE_UPSTREAM,
            )
        return _template_fallback_result(
            weather,
            error_code=ERROR_CODE_API_NON_RETRYABLE,
            warnings_de_en=[
                "Die Eventsuche ist aktuell nicht verfügbar. / Event search is currently unavailable."
            ],
            errors_de_en=[
                "Bitte Eingaben und Konfiguration prüfen; der Fehler ist nicht automatisch retrybar. / Please review inputs and configuration; this error is not automatically retryable."
            ],
        )
