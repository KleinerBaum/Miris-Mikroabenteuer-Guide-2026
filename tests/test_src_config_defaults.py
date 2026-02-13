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
