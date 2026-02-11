from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any, Callable

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from mikroabenteuer.google.auth import get_credentials
from mikroabenteuer.google.schemas import CalendarEventInput

LOGGER = logging.getLogger(__name__)
CALENDAR_ID = "primary"


def safe_api_call(func: Callable[[], Any], retries: int = 3) -> Any:
    for attempt in range(retries):
        try:
            return func()
        except HttpError as exc:
            LOGGER.error("Google API call failed: %s", exc)
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Unreachable retry state")


def get_calendar_service(user_key: str) -> Resource:
    creds = get_credentials(user_key)
    return build("calendar", "v3", credentials=creds)


def create_event(user_key: str, event_input: CalendarEventInput) -> dict[str, Any]:
    service = get_calendar_service(user_key)
    end_time = event_input.start_time + timedelta(minutes=event_input.duration_minutes)
    event = {
        "summary": event_input.title,
        "description": event_input.description,
        "start": {
            "dateTime": event_input.start_time.isoformat(),
            "timeZone": event_input.timezone,
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": event_input.timezone,
        },
    }
    return safe_api_call(
        lambda: service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    )


def list_events(user_key: str, max_results: int = 10) -> dict[str, Any]:
    service = get_calendar_service(user_key)
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
