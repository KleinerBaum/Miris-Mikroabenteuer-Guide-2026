from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int, base_delay: float
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Retry function with exponential backoff.

    The wrapped function is called up to ``max_attempts`` times.
    Delay grows as ``base_delay * (2 ** attempt_index)``.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if base_delay < 0:
        raise ValueError("base_delay must be >= 0")

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    if attempt == max_attempts - 1:
                        break
                    sleep_for = base_delay * (2**attempt)
                    if sleep_for > 0:
                        time.sleep(sleep_for)

            assert last_error is not None
            raise last_error

        return wrapper

    return decorator
