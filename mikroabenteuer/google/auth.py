from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES: list[str] = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRETS_DIR = BASE_DIR / "secrets"
TOKENS_DIR = SECRETS_DIR / "google_tokens"
CLIENT_SECRET_PATH = SECRETS_DIR / "google_client_secret.json"
DEFAULT_REDIRECT_URI = "https://mikrocarla.streamlit.app/"


class OAuthConfigurationError(RuntimeError):
    """Raised when OAuth credentials are not configured."""


def _safe_user_key(user_key: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]", "_", user_key).strip("_")
    if not sanitized:
        raise ValueError("user_key must contain at least one safe character")
    return sanitized


def token_path_for_user(user_key: str) -> Path:
    return TOKENS_DIR / f"{_safe_user_key(user_key)}.json"


def _build_flow(state: str | None = None) -> Flow:
    if not CLIENT_SECRET_PATH.exists():
        raise OAuthConfigurationError(
            "Missing OAuth client file at secrets/google_client_secret.json"
        )
    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRET_PATH),
        scopes=SCOPES,
        redirect_uri=DEFAULT_REDIRECT_URI,
    )
    return flow


def build_authorization_url(user_key: str, state: str) -> str:
    _ = _safe_user_key(user_key)
    flow = _build_flow(state=state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_code_and_store_token(user_key: str, code: str) -> Credentials:
    flow = _build_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials
    persist_credentials(user_key=user_key, credentials=credentials)
    return credentials


def persist_credentials(user_key: str, credentials: Credentials) -> None:
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    token_path = token_path_for_user(user_key)
    token_path.write_text(credentials.to_json(), encoding="utf-8")


def get_credentials(user_key: str) -> Credentials:
    token_path = token_path_for_user(user_key)
    if not token_path.exists():
        raise OAuthConfigurationError(
            "No OAuth token found for this user. Connect Google first."
        )

    raw_data: dict[str, Any] = json.loads(token_path.read_text(encoding="utf-8"))
    credentials = Credentials.from_authorized_user_info(raw_data, SCOPES)

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        persist_credentials(user_key=user_key, credentials=credentials)

    if not credentials.valid:
        raise OAuthConfigurationError("Stored OAuth token is invalid or expired")

    return credentials
