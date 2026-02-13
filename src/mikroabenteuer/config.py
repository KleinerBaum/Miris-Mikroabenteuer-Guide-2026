# src/mikroabenteuer/config.py
from __future__ import annotations

import os
from dataclasses import dataclass

from .constants import DEFAULT_AREA, DEFAULT_CITY, DEFAULT_TIMEZONE


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    return default


def load_dotenv_if_present() -> None:
    """
    Optional convenience loader. Safe even if python-dotenv isn't installed.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    app_env: str
    log_level: str

    timezone: str
    default_city: str
    default_area: str

    default_postal_code: str
    default_radius_km: float
    default_budget_eur: float
    default_available_minutes: int
    default_effort: str

    enable_llm: bool
    enable_web_search: bool
    openai_api_key: str | None
    openai_model: str

    # Optional: Google integration (only used if you wire it up)
    google_client_secrets_file: str
    google_token_file: str
    gmail_from_email: str
    gmail_to_email: str
    calendar_id: str


def load_config() -> AppConfig:
    load_dotenv_if_present()

    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        timezone=os.getenv("TIMEZONE", DEFAULT_TIMEZONE),
        default_city=os.getenv("DEFAULT_CITY", DEFAULT_CITY),
        default_area=os.getenv("DEFAULT_AREA", DEFAULT_AREA),
        default_postal_code=os.getenv("DEFAULT_POSTAL_CODE", "40215"),
        default_radius_km=float(os.getenv("DEFAULT_RADIUS_KM", "5")),
        default_budget_eur=float(os.getenv("DEFAULT_BUDGET_EUR", "15")),
        default_available_minutes=int(os.getenv("DEFAULT_AVAILABLE_MINUTES", "60")),
        default_effort=os.getenv("DEFAULT_EFFORT", "mittel"),
        enable_llm=_to_bool(os.getenv("ENABLE_LLM"), default=True),
        enable_web_search=_to_bool(os.getenv("ENABLE_WEB_SEARCH"), default=False),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        google_client_secrets_file=os.getenv(
            "GOOGLE_OAUTH_CLIENT_SECRETS_FILE", "client_secret.json"
        ),
        google_token_file=os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "token.json"),
        gmail_from_email=os.getenv("GMAIL_FROM_EMAIL", ""),
        gmail_to_email=os.getenv("GMAIL_TO_EMAIL", ""),
        calendar_id=os.getenv("CALENDAR_ID", ""),
    )
