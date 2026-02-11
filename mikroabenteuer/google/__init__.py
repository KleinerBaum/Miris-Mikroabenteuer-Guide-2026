"""Google API integration helpers for OAuth, Calendar, and Gmail."""

from mikroabenteuer.google.auth import (
    OAuthConfigurationError,
    build_authorization_url,
    exchange_code_and_store_token,
)
from mikroabenteuer.google.calendar_service import create_event, list_events
from mikroabenteuer.google.gmail_service import send_html_email

__all__ = [
    "OAuthConfigurationError",
    "build_authorization_url",
    "exchange_code_and_store_token",
    "create_event",
    "list_events",
    "send_html_email",
]
