from __future__ import annotations

from datetime import date

from mikroabenteuer.ics import build_ics_event


def test_build_ics_contains_required_fields() -> None:
    payload = build_ics_event(
        day=date(2026, 1, 1),
        summary="Wald, Spaß",
        description="Zeile 1\nZeile 2",
        location="Volksgarten",
    )
    text = payload.decode("utf-8")

    assert "BEGIN:VCALENDAR" in text
    assert "BEGIN:VEVENT" in text
    assert "SUMMARY:Wald\\, Spaß" in text
    assert "DESCRIPTION:Zeile 1\\nZeile 2" in text
    assert text.endswith("\r\n")
