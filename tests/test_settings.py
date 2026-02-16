from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.mikroabenteuer.settings import RuntimeSettings


def test_runtime_settings_accepts_missing_openai_when_llm_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LLM", "0")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = RuntimeSettings()

    assert settings.enable_llm is False
    assert settings.openai_api_key is None


def test_runtime_settings_requires_openai_for_llm(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LLM", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        RuntimeSettings()


def test_runtime_settings_sanitizes_numeric_limits(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LLM", "0")
    monkeypatch.setenv("MAX_INPUT_CHARS", "10")
    monkeypatch.setenv("MAX_OUTPUT_TOKENS", "50")
    monkeypatch.setenv("TIMEOUT_S", "1")
    monkeypatch.setenv("MAX_REQUESTS_PER_SESSION", "0")

    settings = RuntimeSettings()

    assert settings.max_input_chars == 200
    assert settings.max_output_tokens == 100
    assert settings.timeout_s == 5.0
    assert settings.max_requests_per_session == 1


def test_runtime_settings_reads_openai_nested_secret(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LLM", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "src.mikroabenteuer.settings.st.secrets",
        {"openai": {"api_key": "sk-test"}},
    )

    settings = RuntimeSettings()

    assert settings.openai_api_key == "sk-test"


def test_runtime_settings_reads_openai_top_level_secret(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LLM", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "src.mikroabenteuer.settings.st.secrets",
        {"OPENAI_API_KEY": "sk-test-top-level"},
    )

    settings = RuntimeSettings()

    assert settings.openai_api_key == "sk-test-top-level"


def test_runtime_settings_model_defaults(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LLM", "0")
    monkeypatch.delenv("OPENAI_MODEL_PLAN", raising=False)
    monkeypatch.delenv("OPENAI_MODEL_EVENTS_FAST", raising=False)
    monkeypatch.delenv("OPENAI_MODEL_EVENTS_ACCURATE", raising=False)

    settings = RuntimeSettings()

    assert settings.openai_model_plan == "gpt-4o-mini"
    assert settings.openai_model_events_fast == "gpt-4o-mini"
    assert settings.openai_model_events_accurate == "o3-mini"
