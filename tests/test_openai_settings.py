from __future__ import annotations

from src.mikroabenteuer.openai_settings import resolve_openai_api_key


def test_resolve_openai_api_key_prefers_environment() -> None:
    env = {"OPENAI_API_KEY": "env-key"}
    secrets = {"openai": {"api_key": "secret-key"}}

    resolved = resolve_openai_api_key(env=env, secrets=secrets)

    assert resolved == "env-key"


def test_resolve_openai_api_key_reads_streamlit_secret_shape() -> None:
    secrets = {"openai": {"api_key": "secret-key"}}

    resolved = resolve_openai_api_key(env={}, secrets=secrets)

    assert resolved == "secret-key"


def test_resolve_openai_api_key_returns_none_when_missing() -> None:
    resolved = resolve_openai_api_key(env={}, secrets={})

    assert resolved is None
