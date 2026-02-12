# src/mikroabenteuer/gcal_api.py
from __future__ import annotations

from datetime import datetime, timedelta


def insert_calendar_event(
    creds,
    *,
    calendar_id: str,
    summary: str,
    description: str,
    location: str,
    start_dt: datetime,
    duration_minutes: int = 60,
    timezone: str = "Europe/Berlin",
) -> dict:
    """
    Create a Calendar event via Google Calendar API.
    """
    from googleapiclient.discovery import build  # type: ignore

    end_dt = start_dt + timedelta(minutes=max(15, duration_minutes))

    body = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone},
    }

    service = build("calendar", "v3", credentials=creds)
    return service.events().insert(calendarId=calendar_id, body=body).execute()
