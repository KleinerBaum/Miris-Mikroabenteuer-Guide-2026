from __future__ import annotations

from datetime import date, time

from src.mikroabenteuer.models import (
    ActivitySearchCriteria,
    DevelopmentDomain,
    TimeWindow,
)
from src.mikroabenteuer.openai_activity_service import _build_user_prompt
from src.mikroabenteuer.pii_redaction import redact_pii


def test_redact_pii_replaces_common_identifiers() -> None:
    text = (
        "My name is Max Mustermann. Reach me at max@example.com, "
        "+49 170 1234567, and Musterstraße 12."
    )

    redacted = redact_pii(text)

    assert "Max Mustermann" not in redacted
    assert "max@example.com" not in redacted
    assert "+49 170 1234567" not in redacted
    assert "Musterstraße 12" not in redacted
    assert "[REDACTED_NAME]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_ADDRESS]" in redacted


def test_build_user_prompt_redacts_pii_from_outbound_llm_text() -> None:
    criteria = ActivitySearchCriteria(
        plz="40215",
        radius_km=5.0,
        date=date(2026, 5, 10),
        time_window=TimeWindow(start=time(9, 0), end=time(11, 0)),
        effort="mittel",
        budget_eur_max=20.0,
        topics=["Natur"],
        location_preference="mixed",
        goals=[DevelopmentDomain.language],
        constraints=["Call me at +49 170 1234567 and email me@example.org"],
        max_suggestions=3,
    )

    prompt = _build_user_prompt(criteria, weather=None, strategy=None)

    assert "+49 170 1234567" not in prompt
    assert "me@example.org" not in prompt
    assert "[REDACTED_PHONE]" in prompt
    assert "@" not in prompt
