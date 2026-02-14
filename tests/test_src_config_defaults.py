from __future__ import annotations

from src.mikroabenteuer.config import load_config


def test_enable_llm_defaults_to_true(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_LLM", raising=False)

    cfg = load_config()

    assert cfg.enable_llm is True


def test_enable_llm_can_be_disabled_via_env(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LLM", "0")

    cfg = load_config()

    assert cfg.enable_llm is False


def test_limit_defaults_are_loaded(monkeypatch) -> None:
    monkeypatch.delenv("MAX_INPUT_CHARS", raising=False)
    monkeypatch.delenv("MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("TIMEOUT_S", raising=False)
    monkeypatch.delenv("MAX_REQUESTS_PER_SESSION", raising=False)

    cfg = load_config()

    assert cfg.max_input_chars == 4000
    assert cfg.max_output_tokens == 800
    assert cfg.timeout_s == 45.0
    assert cfg.max_requests_per_session == 10


def test_limit_values_are_sanitized(monkeypatch) -> None:
    monkeypatch.setenv("MAX_INPUT_CHARS", "10")
    monkeypatch.setenv("MAX_OUTPUT_TOKENS", "5")
    monkeypatch.setenv("TIMEOUT_S", "1")
    monkeypatch.setenv("MAX_REQUESTS_PER_SESSION", "0")

    cfg = load_config()

    assert cfg.max_input_chars == 200
    assert cfg.max_output_tokens == 100
    assert cfg.timeout_s == 5.0
    assert cfg.max_requests_per_session == 1
