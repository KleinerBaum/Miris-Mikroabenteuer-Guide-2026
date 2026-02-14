from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st
from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from streamlit.errors import StreamlitSecretNotFoundError

from .config import AppConfig
from .constants import DEFAULT_AREA, DEFAULT_CITY, DEFAULT_TIMEZONE


class RuntimeSettings(BaseSettings):
    """Runtime settings loaded from environment variables and Streamlit secrets."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    timezone: str = DEFAULT_TIMEZONE
    default_city: str = DEFAULT_CITY
    default_area: str = DEFAULT_AREA

    default_postal_code: str = "40215"
    default_radius_km: float = 5.0
    default_budget_eur: float = 15.0
    default_available_minutes: int = 60
    default_effort: str = "mittel"

    enable_llm: bool = True
    enable_web_search: bool = False
    openai_api_key: str | None = Field(default=None, min_length=1)
    openai_model: str = "gpt-5-mini"
    max_input_chars: int = 4000
    max_output_tokens: int = 800
    timeout_s: float = 45.0
    max_requests_per_session: int = 10

    google_client_secrets_file: str = "client_secret.json"
    google_token_file: str = "token.json"
    gmail_from_email: str = ""
    gmail_to_email: str = ""
    calendar_id: str = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            cls._streamlit_secret_settings,
            file_secret_settings,
        )

    @classmethod
    def _streamlit_secret_settings(cls) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        try:
            for key in (
                "OPENAI_API_KEY",
                "APP_ENV",
                "LOG_LEVEL",
                "TIMEZONE",
            ):
                value = st.secrets.get(key)
                if isinstance(value, str) and value.strip():
                    merged[key] = value

            openai = st.secrets.get("openai")
            if isinstance(openai, Mapping):
                secret_key = openai.get("api_key")
                if isinstance(secret_key, str) and secret_key.strip():
                    merged["OPENAI_API_KEY"] = secret_key
        except StreamlitSecretNotFoundError:
            return {}

        return merged

    @model_validator(mode="after")
    def validate_required_keys(self) -> RuntimeSettings:
        if self.enable_llm and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when ENABLE_LLM=true. "
                "Set it via environment variable or Streamlit secrets.openai.api_key."
            )

        self.max_input_chars = max(200, self.max_input_chars)
        self.max_output_tokens = max(100, self.max_output_tokens)
        self.timeout_s = max(5.0, self.timeout_s)
        self.max_requests_per_session = max(1, self.max_requests_per_session)
        return self

    def to_app_config(self) -> AppConfig:
        return AppConfig(**self.model_dump())


def load_runtime_config() -> AppConfig:
    return RuntimeSettings().to_app_config()


def render_missing_config_ui(error: ValidationError) -> None:
    st.error(
        "❌ Fehlende Konfiguration / Missing configuration",
        icon="🚫",
    )
    st.markdown(
        """
Die App wurde aus Sicherheitsgründen nicht gestartet, weil Pflichtwerte fehlen.
The app did not start for safety reasons because required values are missing.

Bitte setzen / Please set:
- `OPENAI_API_KEY` als Umgebungsvariable **oder** `secrets.toml` mit:
  ```toml
  [openai]
  api_key = "sk-..."
  ```
- Optional zum lokalen Testen: `ENABLE_LLM=false`
        """
    )

    details = "\n".join(f"- {item['msg']}" for item in error.errors())
    st.code(details, language="text")
    st.stop()
