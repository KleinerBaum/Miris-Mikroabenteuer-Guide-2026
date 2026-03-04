from __future__ import annotations

import sys
from dataclasses import replace
from datetime import date, time
from types import SimpleNamespace

from mikroabenteuer.config import load_config
from mikroabenteuer.models import (
    ActivityPlan,
    ActivitySearchCriteria,
    MicroAdventure,
    TimeWindow,
)
from mikroabenteuer.openai_activity_service import suggest_activities
from mikroabenteuer.openai_gen import generate_activity_plan


class _RetryableError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"http-{status_code}")
        self.status_code = status_code


class _FakeResponses:
    def __init__(self, behavior: list[object]) -> None:
        self._behavior = behavior
        self.calls = 0
        self.parse_calls = 0
        self.create_calls = 0
        self.last_parse_kwargs: dict[str, object] = {}
        self.last_create_kwargs: dict[str, object] = {}

    def _next(self) -> object:
        current = self._behavior.pop(0)
        if isinstance(current, Exception):
            raise current
        return current

    def parse(self, **kwargs: object) -> object:
        self.calls += 1
        self.parse_calls += 1
        self.last_parse_kwargs = kwargs
        return self._next()

    def create(self, **kwargs: object) -> object:
        self.calls += 1
        self.create_calls += 1
        self.last_create_kwargs = kwargs
        return self._next()


class _FakeOpenAIClient:
    def __init__(self, behavior: list[object]) -> None:
        self.responses = _FakeResponses(behavior)


class _FakeOpenAI:
    behavior: list[object] = []
    last_client: _FakeOpenAIClient | None = None

    def __init__(self, **_: object) -> None:
        client = _FakeOpenAIClient(self.__class__.behavior)
        self.__class__.last_client = client
        self.responses = client.responses


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


def test_suggest_activities_retries_retryable_errors_then_returns(monkeypatch) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        _RetryableError(429),
        _RetryableError(503),
        SimpleNamespace(output_parsed=module.ActivitySuggestionResult()),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.errors_de_en == []
    assert _FakeOpenAI.last_client is not None
    assert _FakeOpenAI.last_client.responses.calls == 3


def test_suggest_activities_returns_curated_fallback_on_repeated_5xx(
    monkeypatch,
) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        _RetryableError(500),
        _RetryableError(502),
        _RetryableError(503),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.suggestions == []
    assert any("safe curated templates" in msg for msg in result.errors_de_en)


def test_generate_activity_plan_returns_safe_fallback_after_retryable_failures(
    monkeypatch,
) -> None:
    from mikroabenteuer import openai_gen as module

    _FakeOpenAI.behavior = [
        _RetryableError(503),
        _RetryableError(503),
        _RetryableError(503),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    cfg = replace(load_config(), enable_llm=True, openai_api_key="test-key")

    plan = generate_activity_plan(
        cfg, _build_micro_adventure(), _build_criteria(), None
    )

    assert isinstance(plan, ActivityPlan)
    assert "Sicheres Alternativprogramm" in plan.title


def test_suggest_activities_uses_configured_event_models(monkeypatch) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(output_parsed=module.ActivitySuggestionResult())
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    suggest_activities(
        _build_criteria(),
        mode="genau",
        model_fast="event-fast-model",
        model_accurate="event-accurate-model",
    )

    assert _FakeOpenAI.last_client is not None
    assert (
        _FakeOpenAI.last_client.responses.last_parse_kwargs["model"]
        == "event-accurate-model"
    )


def test_generate_activity_plan_uses_configured_plan_model(monkeypatch) -> None:
    from mikroabenteuer import openai_gen as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(
            output_parsed=module.ActivityPlan(
                title="Test",
                summary="Test",
                steps=["Schritt"],
                safety_notes=["Hinweis"],
                parent_child_prompts=["Say: x Do: y"],
                variants=["Plan B"],
                supports=["Sprache"],
            )
        )
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    cfg = replace(
        load_config(),
        enable_llm=True,
        openai_api_key="test-key",
        openai_model_plan="plan-model-x",
    )

    generate_activity_plan(cfg, _build_micro_adventure(), _build_criteria(), None)

    assert _FakeOpenAI.last_client is not None
    assert (
        _FakeOpenAI.last_client.responses.last_parse_kwargs["model"] == "plan-model-x"
    )


def test_suggest_activities_marks_missing_api_key(monkeypatch) -> None:
    from mikroabenteuer import openai_activity_service as module

    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "")

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.error_code == module.ERROR_CODE_MISSING_API_KEY
    assert result.error_hint_de_en is not None


def test_suggest_activities_marks_non_retryable_api_error(monkeypatch) -> None:
    from mikroabenteuer import openai_activity_service as module

    class _NonRetryableError(Exception):
        status_code = 400

    _FakeOpenAI.behavior = [_NonRetryableError("bad request")]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.error_code == module.ERROR_CODE_API_NON_RETRYABLE
    assert result.error_hint_de_en is not None


def test_suggest_activities_marks_structured_output_error(monkeypatch) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(output_parsed=None),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.error_code == module.ERROR_CODE_STRUCTURED_OUTPUT
    assert result.error_hint_de_en is not None


def test_suggest_activities_recovers_after_schema_repair(monkeypatch) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(output_parsed=module.ActivitySuggestionResult()),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert module.RECOVERY_MARKER_SCHEMA_REPAIR in result.warnings_de_en
    assert result.error_code is None


def test_suggest_activities_uses_best_effort_from_create_after_parse_failures(
    monkeypatch,
) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(
            output=[
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                "Familienflohmarkt im Park\n"
                                "Treffpunkt am Haupteingang, kleine Mitmach-Stationen.\n"
                                "Quelle: https://example.org/event"
                            ),
                        }
                    ]
                }
            ]
        ),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.error_code is None
    assert result.suggestions
    assert result.suggestions[0].source_urls == ["https://example.org/event"]
    assert module.RECOVERY_MARKER_SCHEMA_REPAIR in result.warnings_de_en
    assert _FakeOpenAI.last_client is not None
    assert _FakeOpenAI.last_client.responses.create_calls == 1


def test_suggest_activities_returns_structured_fallback_when_create_unusable(
    monkeypatch,
) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(
            output=[{"content": [{"type": "output_text", "text": "Ohne URL"}]}]
        ),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.error_code == module.ERROR_CODE_STRUCTURED_OUTPUT
    assert result.error_hint_de_en is not None
    assert _FakeOpenAI.last_client is not None
    assert _FakeOpenAI.last_client.responses.create_calls == 1


def test_suggest_activities_uses_best_effort_after_second_invalid_response(
    monkeypatch,
) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(output_parsed=None),
        SimpleNamespace(
            output_text=(
                "Familienflohmarkt im Park\n"
                "Treffpunkt am Haupteingang, kleine Mitmach-Stationen.\n"
                "Quelle: https://example.org/event"
            )
        ),
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.error_code is None
    assert result.suggestions
    assert result.suggestions[0].source_urls == ["https://example.org/event"]
    assert module.RECOVERY_MARKER_SCHEMA_REPAIR in result.warnings_de_en


def test_suggest_activities_fills_missing_reason_without_invalidating(
    monkeypatch,
) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(
            output_parsed={
                "suggestions": [
                    {
                        "title": "Spielplatz-Spaziergang",
                        "indoor_outdoor": "unknown",
                        "source_urls": ["https://example.org/tipp"],
                    }
                ]
            }
        )
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.errors_de_en == []
    assert result.error_code is None
    assert result.suggestions
    assert (
        result.suggestions[0].reason_de_en
        == "Keine Begründung geliefert. / No rationale provided."
    )
    assert result.suggestions[0].indoor_outdoor == "mixed"


def test_suggest_activities_fills_empty_title_with_fallback(monkeypatch) -> None:
    from mikroabenteuer import openai_activity_service as module

    _FakeOpenAI.behavior = [
        SimpleNamespace(
            output_parsed={
                "suggestions": [
                    {
                        "title": "   ",
                        "reason_de_en": "Grund / reason",
                        "source_urls": ["https://example.org/tipp"],
                    }
                ]
            }
        )
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(_build_criteria(), mode="schnell")

    assert result.suggestions
    assert result.suggestions[0].title == "Aktivität / Activity"


def test_suggest_activities_long_context_keeps_structured_output_stable(
    monkeypatch,
) -> None:
    from mikroabenteuer import openai_activity_service as module

    long_constraints = [f"constraint-{idx}-" + ("x" * 70) for idx in range(8)]
    long_materials = [f"material-{idx}-" + ("y" * 25) for idx in range(8)]
    criteria = _build_criteria().model_copy(
        update={
            "constraints": long_constraints,
            "available_materials": long_materials,
            "topics": ["natur", "kunst", "musik", "sport", "technik", "lernen"],
            "max_suggestions": 7,
        }
    )

    _FakeOpenAI.behavior = [
        SimpleNamespace(
            output_parsed={
                "suggestions": [
                    {
                        "title": f"Event {idx}",
                        "reason_de_en": "Kurz / concise",
                        "description": "Kompakt",
                        "source_urls": [
                            f"https://example.org/event-{idx}",
                            f"https://example.org/event-{idx}/more",
                            f"https://example.org/event-{idx}/extra",
                        ],
                    }
                    for idx in range(4)
                ]
            }
        )
    ]
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    monkeypatch.setattr(module, "configure_openai_api_key", lambda: None)
    monkeypatch.setattr(module, "resolve_openai_api_key", lambda: "test-key")
    monkeypatch.setattr(module, "moderate_text", lambda *_args, **_kwargs: False)

    result = suggest_activities(criteria, mode="schnell")

    assert result.error_code is None
    assert len(result.suggestions) == 4
    assert all(len(item.source_urls) <= 2 for item in result.suggestions)
    assert _FakeOpenAI.last_client is not None
    user_prompt = _FakeOpenAI.last_client.responses.last_parse_kwargs["input"][1][
        "content"
    ]
    assert "Gib maximal 4 Vorschläge" in str(user_prompt)
