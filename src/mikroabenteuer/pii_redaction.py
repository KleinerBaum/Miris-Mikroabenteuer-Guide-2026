from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s\-./]?)?(?:\(?\d{2,5}\)?[\s\-./]?)\d(?:[\s\-./]?\d){5,}(?!\w)"
)
_ADDRESS_RE = re.compile(
    r"\b(?:[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){0,3})\s+\d{1,4}[a-zA-Z]?\b"
)
_NAME_RE = re.compile(
    r"\b(?:mein\s+name\s+ist|my\s+name\s+is|ich\s+hei(?:ß|ss)e)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){0,2})\b",
    flags=re.IGNORECASE,
)


def redact_pii(text: str) -> str:
    """Redact common personal identifiers from free text before LLM usage."""

    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = _ADDRESS_RE.sub("[REDACTED_ADDRESS]", redacted)
    redacted = _NAME_RE.sub(_name_replacer, redacted)
    return redacted


def _name_replacer(match: re.Match[str]) -> str:
    prefix = match.group(0)
    name = match.group(1)
    return prefix.replace(name, "[REDACTED_NAME]")
