from __future__ import annotations

from dataclasses import replace
from datetime import date, time
from types import SimpleNamespace

from mikroabenteuer.config import load_config
from mikroabenteuer.moderation import SAFE_BLOCK_MESSAGE_DE_EN
from mikroabenteuer.models import (
    ActivitySearchCriteria,
    TimeWindow,
)
from mikroabenteuer.openai_activity_service import suggest_activities


def _criteria() -> ActivitySearchCriteria:
    return ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 2, 14),
        time_window=TimeWindow(start=time(9, 0), end=time(10, 0)),
        effort="mittel",
        budget_eur_max=20.0,
        topics=["natur"],
    )


def _moderation_response(flagged: bool) -> SimpleNamespace:
    return SimpleNamespace(
        results=[
            SimpleNamespace(
                flagged=flagged,
                categories=SimpleNamespace(violence=flagged),
            )
        ]
    )


def test_suggest_activities_blocks_when_input_moderation_is_flagged(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "mikroabenteuer.openai_activity_service.configure_openai_api_key",
        lambda: None,
    )
    monkeypatch.setattr(
        "mikroabenteuer.openai_activity_service.resolve_openai_api_key",
        lambda: "test-key",
    )

    class _FakeClient:
        def __init__(self, **_: object) -> None:
            self.moderations = SimpleNamespace(
                create=lambda **__: _moderation_response(flagged=True)
            )
            self.responses = SimpleNamespace(
                parse=lambda **__: (_ for _ in ()).throw(
                    AssertionError(
                        "responses.parse must not be called when input is flagged"
                    )
                )
            )

    monkeypatch.setattr("openai.OpenAI", _FakeClient)

    result = suggest_activities(_criteria(), mode="schnell")

    assert result.suggestions == []
    assert result.errors_de_en == [SAFE_BLOCK_MESSAGE_DE_EN]


def test_openai_activity_service_exposes_moderation_block_as_ui_error(
    monkeypatch,
) -> None:
    from app import OpenAIActivityService

    monkeypatch.setattr(
        "mikroabenteuer.openai_activity_service.suggest_activities",
        lambda *args, **kwargs: SimpleNamespace(
            suggestions=[],
            sources=[],
            warnings_de_en=[],
            errors_de_en=[SAFE_BLOCK_MESSAGE_DE_EN],
        ),
    )

    cfg = replace(load_config(), enable_llm=True)
    service = OpenAIActivityService(cfg=cfg)
    result = service.search_events(_criteria(), weather=None, mode="schnell")

    assert result["suggestions"] == []
    assert result["errors"] == [SAFE_BLOCK_MESSAGE_DE_EN]
