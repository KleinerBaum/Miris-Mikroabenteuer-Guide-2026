from __future__ import annotations

from pathlib import Path


def test_no_hardcoded_duesseldorf_in_event_weather_path() -> None:
    app_text = Path("app.py").read_text(encoding="utf-8")
    service_text = Path("src/mikroabenteuer/openai_activity_service.py").read_text(
        encoding="utf-8"
    )

    assert "Düsseldorf" not in app_text
    assert "Düsseldorf" not in service_text
