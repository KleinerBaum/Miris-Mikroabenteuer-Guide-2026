from __future__ import annotations

import logging
from typing import Any

from .pii_redaction import redact_pii

logger = logging.getLogger(__name__)

SAFE_BLOCK_MESSAGE_DE_EN = (
    "Inhalt wurde aus Sicherheitsgründen blockiert. Bitte formuliere die Anfrage neutral und ohne sensible/problematische Inhalte. "
    "/ Content was blocked for safety reasons. Please rephrase with neutral and safe wording."
)


def moderate_text(client: Any, *, text: str, stage: str) -> bool:
    """Return True when OpenAI moderation flags the given text.

    Logging never includes the moderated text to avoid storing potentially sensitive content.
    """

    response = client.moderations.create(
        model="omni-moderation-latest",
        input=redact_pii(text),
    )
    result = response.results[0]
    flagged = bool(getattr(result, "flagged", False))

    if flagged:
        categories_obj = getattr(result, "categories", None)
        category_names: list[str] = []
        if categories_obj is not None:
            category_names = [
                key
                for key, value in vars(categories_obj).items()
                if isinstance(value, bool) and value
            ]
        logger.warning(
            "Moderation blocked content at stage=%s categories=%s",
            stage,
            ",".join(category_names) or "none",
        )
    return flagged
