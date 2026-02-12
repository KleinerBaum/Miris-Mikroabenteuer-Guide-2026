# src/mikroabenteuer/google_auth.py
from __future__ import annotations

from pathlib import Path
from typing import List

# Imports are lazy in get_credentials() to keep base app runnable without Google deps.


def get_credentials(
    client_secrets_file: str,
    token_file: str,
    scopes: List[str],
):
    """
    Returns Google OAuth credentials.

    - If token_file exists, we load it.
    - Else we start InstalledAppFlow and store token_file.

    This is a pragmatic default for local/dev usage.
    For production HTTPS OAuth redirects, you'll typically run your own OAuth callback
    handler and store tokens securely – this function can be replaced later.
    """
    # Lazy imports
    from google.oauth2.credentials import Credentials  # type: ignore
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore

    token_path = Path(token_file)
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes=scopes)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes=scopes
        )
        # Local server flow for dev
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds
