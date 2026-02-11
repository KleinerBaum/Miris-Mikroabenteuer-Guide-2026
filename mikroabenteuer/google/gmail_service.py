from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mikroabenteuer.email_templates import build_html_mail
from mikroabenteuer.ics_builder import build_ics
from mikroabenteuer.models import Adventure
from mikroabenteuer.retry import retry_with_backoff

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "secrets/token.json")
CLIENT_SECRET_FILE = os.getenv(
    "GOOGLE_CLIENT_SECRET_FILE", "secrets/client_secret.json"
)
DAILY_MAIL_TO = os.getenv("DAILY_MAIL_TO", "")
DAILY_MAIL_FROM = os.getenv("DAILY_MAIL_FROM", "")


class GmailConfigError(RuntimeError):
    """Raised when Gmail configuration is incomplete."""


def get_gmail_service():
    """Authenticate and build Gmail API service."""
    creds: Credentials | None = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


@retry_with_backoff(max_attempts=3, base_delay=1)
def send_daily_mail(adventure: Adventure) -> dict[str, object]:
    """Send a daily adventure mail with HTML and ICS attachment."""
    if not DAILY_MAIL_TO or not DAILY_MAIL_FROM:
        raise GmailConfigError(
            "Set DAILY_MAIL_TO and DAILY_MAIL_FROM in the environment."
        )

    service = get_gmail_service()

    message = MIMEMultipart("mixed")
    message["to"] = DAILY_MAIL_TO
    message["from"] = DAILY_MAIL_FROM
    message["subject"] = f"Mikroabenteuer: {adventure.title}"

    html_body = build_html_mail(adventure)
    message.attach(MIMEText(html_body, "html", "utf-8"))

    ics_content = build_ics(
        title=adventure.title,
        description=adventure.description,
        start_time=datetime.now(tz=timezone.utc),
    )

    ics_part = MIMEBase("text", "calendar", method="PUBLISH", name="event.ics")
    ics_part.set_payload(ics_content.encode("utf-8"))
    encoders.encode_base64(ics_part)
    ics_part.add_header("Content-Disposition", 'attachment; filename="event.ics"')
    ics_part.add_header("Content-Type", "text/calendar; charset=UTF-8; method=PUBLISH")
    message.attach(ics_part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()

    return result
