from __future__ import annotations

import base64
from datetime import UTC, datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from googleapiclient.discovery import Resource, build

from mikroabenteuer.google.auth import get_credentials
from mikroabenteuer.google.calendar_service import safe_api_call
from mikroabenteuer.google.schemas import DailyDigestInput, WeatherAdventureSuggestion


def get_gmail_service(user_key: str) -> Resource:
    creds = get_credentials(user_key)
    return build("gmail", "v1", credentials=creds)


def build_weather_suggestion(weather_summary: str) -> WeatherAdventureSuggestion:
    summary = weather_summary.lower()
    if "rain" in summary or "regen" in summary:
        return WeatherAdventureSuggestion(
            weather_summary=weather_summary,
            activity_focus_en=(
                "Try a short puddle walk in Düsseldorf Volksgarten with rain gear "
                "and finish with a warm drink at home."
            ),
            activity_focus_de=(
                "Macht einen kurzen Pfützen-Spaziergang im Düsseldorfer Volksgarten "
                "mit Regenkleidung und beendet den Tag mit einem warmen Getränk daheim."
            ),
        )
    if "sun" in summary or "sonne" in summary or "clear" in summary:
        return WeatherAdventureSuggestion(
            weather_summary=weather_summary,
            activity_focus_en=(
                "Plan a light nature bingo in Volksgarten and add a picnic break in the sun."
            ),
            activity_focus_de=(
                "Plant ein leichtes Natur-Bingo im Volksgarten und ergänzt eine sonnige Picknickpause."
            ),
        )
    return WeatherAdventureSuggestion(
        weather_summary=weather_summary,
        activity_focus_en="Choose a flexible walk route around Volksgarten with weather-appropriate layers.",
        activity_focus_de=(
            "Wählt eine flexible Runde rund um den Volksgarten mit wetterangepasster Kleidung."
        ),
    )


def build_ics_attachment(
    *,
    title: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
    location: str,
) -> bytes:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dt_start = start_time.strftime("%Y%m%dT%H%M%S")
    dt_end = end_time.strftime("%Y%m%dT%H%M%S")
    payload = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Mikroabenteuer//DE",
            "BEGIN:VEVENT",
            f"DTSTAMP:{timestamp}",
            f"DTSTART;TZID=Europe/Berlin:{dt_start}",
            f"DTEND;TZID=Europe/Berlin:{dt_end}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{location}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    return payload.encode("utf-8")


def build_daily_scheduler_email_html(data: DailyDigestInput) -> str:
    suggestion = build_weather_suggestion(data.weather_summary)
    scheduled_label = data.scheduled_for.strftime("%H:%M")
    return f"""
    <div style=\"font-family:Arial,sans-serif;line-height:1.5;color:#1f2937;\">
      <h2 style=\"margin-bottom:8px;\">🌿 Daily Adventure Plan / Tages-Abenteuerplan</h2>
      <p style=\"margin-top:0;color:#4b5563;\">Auto-send at {scheduled_label} (Europe/Berlin)</p>
      <h3 style=\"margin-bottom:4px;\">{data.adventure_title}</h3>
      <p>{data.adventure_description}</p>
      <p><strong>Weather / Wetter:</strong> {data.weather_summary}</p>
      <p><strong>EN:</strong> {suggestion.activity_focus_en}</p>
      <p><strong>DE:</strong> {suggestion.activity_focus_de}</p>
      <p style=\"font-size:12px;color:#6b7280;\">Focus area: Düsseldorf Volksgarten.</p>
    </div>
    """.strip()


def send_html_email(
    *,
    user_key: str,
    to: str,
    subject: str,
    html_content: str,
    from_email: str,
    ics_attachment: bytes | None = None,
) -> dict[str, Any]:
    service = get_gmail_service(user_key)

    message = MIMEMultipart()
    message["to"] = to
    message["from"] = from_email
    message["subject"] = subject
    message.attach(MIMEText(html_content, "html", _charset="utf-8"))

    if ics_attachment is not None:
        ics_part = MIMEApplication(ics_attachment, _subtype="ics")
        ics_part.add_header(
            "Content-Disposition", "attachment", filename="abenteuer.ics"
        )
        message.attach(ics_part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    body = {"raw": raw_message}

    return safe_api_call(
        lambda: service.users().messages().send(userId="me", body=body).execute()
    )
