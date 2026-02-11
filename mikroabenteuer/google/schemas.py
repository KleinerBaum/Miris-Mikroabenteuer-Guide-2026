from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_secret_path: str
    redirect_uri: str


@dataclass(frozen=True)
class CalendarEventInput:
    title: str
    description: str
    start_time: datetime
    timezone: str = "Europe/Berlin"
    duration_minutes: int = 60


@dataclass(frozen=True)
class WeatherAdventureSuggestion:
    weather_summary: str
    activity_focus_en: str
    activity_focus_de: str


@dataclass(frozen=True)
class DailyDigestInput:
    recipient_email: str
    adventure_title: str
    adventure_description: str
    weather_summary: str
    scheduled_for: datetime
