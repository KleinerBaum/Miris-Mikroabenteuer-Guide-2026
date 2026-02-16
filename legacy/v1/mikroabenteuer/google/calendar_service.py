from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from googleapiclient.discovery import Resource, build

from .api_utils import safe_api_call
from .auth import get_credentials
from .schemas import CalendarEventCreateRequest

CALENDAR_ID = (
    "e2a52f862c8088c82d9f74825b8c39f6069965fdc652472fbf5ec28e891c077e"
    "@group.calendar.google.com"
)
TIME_ZONE = "Europe/Berlin"


def get_calendar_service() -> Resource:
    """Build and return Google Calendar API client."""
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)


def create_event(title: str, description: str, start_time: datetime) -> dict[str, Any]:
    """Create a one-hour event in the configured Google Calendar."""
    service = get_calendar_service()
    payload = CalendarEventCreateRequest(
        title=title,
        description=description,
        start_time=start_time,
    )

    event = {
        "summary": payload.title,
        "description": payload.description,
        "start": {
            "dateTime": payload.start_time.isoformat(),
            "timeZone": TIME_ZONE,
        },
        "end": {
            "dateTime": (payload.start_time + timedelta(hours=1)).isoformat(),
            "timeZone": TIME_ZONE,
        },
    }

    return safe_api_call(
        lambda: service.events()
        .insert(
            calendarId=CALENDAR_ID,
            body=event,
        )
        .execute()
    )


def list_events(max_results: int = 10) -> dict[str, Any]:
    """List upcoming events from the configured Google Calendar."""
    service = get_calendar_service()
    return safe_api_call(
        lambda: service.events()
        .list(
            calendarId=CALENDAR_ID,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
