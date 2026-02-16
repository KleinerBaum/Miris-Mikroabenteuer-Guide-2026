from __future__ import annotations

from mikroabenteuer.openai_activity_service import (
    _truncate_text_with_limit as truncate_events,
)
from mikroabenteuer.openai_gen import _truncate_text_with_limit as truncate_plan


def test_truncate_text_with_limit_noop_when_short() -> None:
    text, truncated = truncate_events("kurz", max_chars=10)

    assert text == "kurz"
    assert truncated is False


def test_truncate_text_with_limit_cuts_long_input() -> None:
    text, truncated = truncate_plan("x" * 50, max_chars=12)

    assert text == "x" * 12
    assert truncated is True
