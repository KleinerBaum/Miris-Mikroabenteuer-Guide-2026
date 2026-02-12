# src/mikroabenteuer/gmail_api.py
from __future__ import annotations

import base64
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


def send_gmail_message(
    creds,
    *,
    user_id: str,
    sender: str,
    to: str,
    subject: str,
    html_body: str,
    ics_bytes: Optional[bytes] = None,
    ics_filename: str = "mikroabenteuer.ics",
) -> dict:
    """
    Send an email via Gmail API with optional ICS attachment.
    """
    # Lazy import to avoid breaking base app when google libs not installed
    from googleapiclient.discovery import build  # type: ignore

    msg = MIMEMultipart("mixed")
    msg["To"] = to
    msg["From"] = sender
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    if ics_bytes:
        part = MIMEApplication(ics_bytes, _subtype="ics")
        part.add_header("Content-Disposition", "attachment", filename=ics_filename)
        part.add_header("Content-Type", "text/calendar; charset=utf-8; method=PUBLISH")
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service = build("gmail", "v1", credentials=creds)
    return service.users().messages().send(userId=user_id, body={"raw": raw}).execute()
