from __future__ import annotations

from datetime import datetime

from mikroabenteuer.google.auth import token_path_for_user
from mikroabenteuer.google.gmail_service import (
    build_ics_attachment,
    build_weather_suggestion,
)


def test_token_path_for_user_sanitizes_value() -> None:
    token_path = token_path_for_user("john+doe@example.com")
    assert token_path.name == "john_doe_example.com.json"


def test_build_weather_suggestion_returns_volksgarten_focus() -> None:
    suggestion = build_weather_suggestion("Rain expected in Düsseldorf")
    assert "Volksgarten" in suggestion.activity_focus_en
    assert "Volksgarten" in suggestion.activity_focus_de


def test_build_ics_attachment_contains_calendar_tokens() -> None:
    ics_payload = build_ics_attachment(
        title="Mikroabenteuer",
        description="Kurzer Spaziergang",
        start_time=datetime(2026, 1, 10, 8, 20),
        end_time=datetime(2026, 1, 10, 9, 20),
        location="Düsseldorf Volksgarten",
    )

    decoded = ics_payload.decode("utf-8")
    assert "BEGIN:VCALENDAR" in decoded
    assert "SUMMARY:Mikroabenteuer" in decoded
    assert "LOCATION:Düsseldorf Volksgarten" in decoded
