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
        self.last_parse_kwargs: dict[str, object] = {}

    def parse(self, **kwargs: object) -> object:
        self.calls += 1
        self.last_parse_kwargs = kwargs
        current = self._behavior.pop(0)
        if isinstance(current, Exception):
            raise current
        return current


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
    assert "Safe fallback plan" in plan.title


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
                supports=["Sprache / Language"],
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
