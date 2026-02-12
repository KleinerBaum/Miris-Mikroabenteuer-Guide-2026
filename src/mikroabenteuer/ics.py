from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4


def _escape_ics(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_ics_event(
    *,
    day: date,
    summary: str,
    description: str,
    location: str,
    tzid: str = "Europe/Berlin",
    start_time_local: time | None = None,
    duration_minutes: int = 60,
) -> bytes:
    uid = f"{uuid4()}@mikroabenteuer.local"
    dtstamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Miris Mikroabenteuer//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"SUMMARY:{_escape_ics(summary)}",
        f"DESCRIPTION:{_escape_ics(description)}",
        f"LOCATION:{_escape_ics(location)}",
    ]

    if start_time_local is None:
        lines.append(f"DTSTART;VALUE=DATE:{day.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{(day + timedelta(days=1)).strftime('%Y%m%d')}")
    else:
        start_local = datetime.combine(day, start_time_local)
        end_local = start_local + timedelta(minutes=max(15, duration_minutes))
        lines.append(f"DTSTART;TZID={tzid}:{start_local.strftime('%Y%m%dT%H%M%S')}")
        lines.append(f"DTEND;TZID={tzid}:{end_local.strftime('%Y%m%dT%H%M%S')}")

    lines.extend(["END:VEVENT", "END:VCALENDAR", ""])
    return "\r\n".join(lines).encode("utf-8")
