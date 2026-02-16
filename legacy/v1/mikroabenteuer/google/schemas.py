from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CalendarEventCreateRequest(BaseModel):
    """Input data for creating a Google Calendar event."""

    title: str
    description: str
    start_time: datetime


class GmailMessageRequest(BaseModel):
    """Input data for sending a Gmail HTML message."""

    to: str
    subject: str
    html_content: str
