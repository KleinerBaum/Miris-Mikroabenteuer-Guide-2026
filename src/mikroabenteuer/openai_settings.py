from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def _load_streamlit_secrets() -> Mapping[str, Any]:
    try:
        return st.secrets
    except StreamlitSecretNotFoundError:
        return {}


def resolve_openai_api_key(
    env: Mapping[str, str] | None = None,
    secrets: Mapping[str, Any] | None = None,
) -> str | None:
    """Resolve API key from environment first, then from Streamlit secrets."""
    environment = env if env is not None else os.environ
    api_key = environment.get("OPENAI_API_KEY")
    if api_key:
        return api_key

    configured_secrets = secrets if secrets is not None else _load_streamlit_secrets()
    openai_section = configured_secrets.get("openai")
    if isinstance(openai_section, Mapping):
        secret_key = openai_section.get("api_key")
        if isinstance(secret_key, str) and secret_key:
            return secret_key

    return None


def configure_openai_api_key() -> str | None:
    """Ensure OPENAI_API_KEY is available in process env from allowed sources."""
    api_key = resolve_openai_api_key()
    if api_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = api_key

    return api_key
