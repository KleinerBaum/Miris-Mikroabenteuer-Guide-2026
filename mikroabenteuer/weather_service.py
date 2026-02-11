from __future__ import annotations

from typing import Any

import requests  # type: ignore[import-untyped]

from mikroabenteuer.retry import retry_with_backoff

DUESSELDORF_LAT = 51.2277
DUESSELDORF_LON = 6.7735
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(RuntimeError):
    """Raised when weather data cannot be resolved."""


@retry_with_backoff(max_attempts=3, base_delay=0.5)
def _fetch_weather_payload() -> dict[str, Any]:
    response = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": DUESSELDORF_LAT,
            "longitude": DUESSELDORF_LON,
            "current": "temperature_2m,precipitation,wind_speed_10m",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if "current" not in payload:
        raise WeatherServiceError("Open-Meteo response misses 'current' section.")

    return payload


def get_weather() -> dict[str, float]:
    """Return current weather metrics for Düsseldorf."""
    payload = _fetch_weather_payload()
    current = payload["current"]
    try:
        return {
            "temperature": float(current["temperature_2m"]),
            "rain": float(current["precipitation"]),
            "wind": float(current["wind_speed_10m"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError("Unexpected weather payload format.") from exc
