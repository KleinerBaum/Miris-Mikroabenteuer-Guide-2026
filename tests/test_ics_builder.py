from __future__ import annotations

from datetime import datetime, timezone

from mikroabenteuer.ics_builder import build_ics


def test_build_ics_contains_required_fields() -> None:
    payload = build_ics(
        title="Wald, Spaß",
        description="Zeile 1\nZeile 2",
        start_time=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert "BEGIN:VCALENDAR" in payload
    assert "BEGIN:VEVENT" in payload
    assert "SUMMARY:Wald\\, Spaß" in payload
    assert "DESCRIPTION:Zeile 1\\nZeile 2" in payload
    assert payload.endswith("\r\n")
