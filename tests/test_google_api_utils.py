from __future__ import annotations

from types import SimpleNamespace

from googleapiclient.errors import HttpError

from mikroabenteuer.google.api_utils import safe_api_call


def _http_error() -> HttpError:
    return HttpError(
        resp=SimpleNamespace(status=500, reason="internal error"),
        content=b"error",
        uri="https://example.invalid",
    )


def test_safe_api_call_retries_then_returns(monkeypatch) -> None:
    attempts = {"count": 0}
    sleeps: list[int] = []

    def fake_sleep(value: int) -> None:
        sleeps.append(value)

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise _http_error()
        return "ok"

    monkeypatch.setattr("mikroabenteuer.google.api_utils.time.sleep", fake_sleep)

    result = safe_api_call(flaky, retries=3)

    assert result == "ok"
    assert attempts["count"] == 3
    assert sleeps == [1, 2]


def test_safe_api_call_raises_after_max_retries(monkeypatch) -> None:
    attempts = {"count": 0}

    def fake_sleep(_: int) -> None:
        return None

    def always_fail() -> str:
        attempts["count"] += 1
        raise _http_error()

    monkeypatch.setattr("mikroabenteuer.google.api_utils.time.sleep", fake_sleep)

    try:
        safe_api_call(always_fail, retries=2)
    except HttpError:
        pass
    else:
        raise AssertionError("Expected HttpError to be raised")

    assert attempts["count"] == 2
