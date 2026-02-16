from __future__ import annotations

import os
from typing import Any

import requests  # type: ignore[import-untyped]

from mikroabenteuer.retry import retry_with_backoff

VOLKSGARTEN_LAT = 51.2149
VOLKSGARTEN_LON = 6.7861
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(RuntimeError):
    """Raised when weather data cannot be resolved."""


def _configured_coordinate(name: str, default: float) -> float:
    configured_value = os.getenv(name)
    if configured_value is None or configured_value.strip() == "":
        return default

    try:
        return float(configured_value)
    except ValueError as exc:
        raise WeatherServiceError(
            f"Environment variable '{name}' must be a float."
        ) from exc


@retry_with_backoff(max_attempts=3, base_delay=0.5)
def _fetch_weather_payload() -> dict[str, Any]:
    latitude = _configured_coordinate("WEATHER_LAT", VOLKSGARTEN_LAT)
    longitude = _configured_coordinate("WEATHER_LON", VOLKSGARTEN_LON)

    response = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
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
    """Return current weather metrics for the configured weather location."""
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
