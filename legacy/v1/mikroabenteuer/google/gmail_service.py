from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from googleapiclient.discovery import Resource, build

from mikroabenteuer.email_templates import build_html_mail
from mikroabenteuer.ics_builder import build_ics
from mikroabenteuer.models import Adventure
from mikroabenteuer.retry import retry_with_backoff

from .api_utils import safe_api_call
from .auth import get_credentials
from .schemas import GmailMessageRequest

DAILY_MAIL_TO = os.getenv("DAILY_MAIL_TO", "")
DAILY_MAIL_FROM = os.getenv("DAILY_MAIL_FROM", "")
DEFAULT_FROM_ADDRESS = os.getenv("GMAIL_FROM_ADDRESS", "gerrit.fabisch2024@gmail.com")


class GmailConfigError(RuntimeError):
    """Raised when Gmail configuration is incomplete."""


def get_gmail_service() -> Resource:
    """Authenticate and build Gmail API service."""
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def send_html_email(to: str, subject: str, html_content: str) -> dict[str, Any]:
    """Send a simple HTML email using Gmail API."""
    payload = GmailMessageRequest(
        to=to,
        subject=subject,
        html_content=html_content,
    )
    service = get_gmail_service()

    message = MIMEText(payload.html_content, "html")
    message["to"] = str(payload.to)
    message["from"] = DEFAULT_FROM_ADDRESS
    message["subject"] = payload.subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    body = {"raw": raw_message}

    return safe_api_call(
        lambda: service.users()
        .messages()
        .send(
            userId="me",
            body=body,
        )
        .execute()
    )


@retry_with_backoff(max_attempts=3, base_delay=1)
def send_daily_mail(adventure: Adventure) -> dict[str, Any]:
    """Send a daily adventure mail with HTML and ICS attachment."""
    if not DAILY_MAIL_TO or not DAILY_MAIL_FROM:
        raise GmailConfigError(
            "Set DAILY_MAIL_TO and DAILY_MAIL_FROM in the environment."
        )

    service = get_gmail_service()

    message = MIMEMultipart("mixed")
    message["to"] = DAILY_MAIL_TO
    message["from"] = DAILY_MAIL_FROM
    message["subject"] = f"Miri & Carla Mikroabenteuer: {adventure.title}"

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
    return safe_api_call(
        lambda: service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )
