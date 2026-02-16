from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

LOGGER = logging.getLogger(__name__)


def safe_api_call(func: Callable[[], T], retries: int = 3) -> T:
    """Execute API call with exponential backoff on transient Google HTTP errors."""
    from googleapiclient.errors import HttpError

    for attempt in range(retries):
        try:
            return func()
        except HttpError as error:
            LOGGER.error("Google API request failed: %s", error)
            if attempt >= retries - 1:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("Unexpected retry loop termination")
