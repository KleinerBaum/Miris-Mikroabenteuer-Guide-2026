# src/mikroabenteuer/weather.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import requests

from .constants import DEFAULT_TIMEZONE


@dataclass(frozen=True)
class WeatherSummary:
    day: date
    temperature_max_c: Optional[float]
    temperature_min_c: Optional[float]
    precipitation_probability_max: Optional[float]
    precipitation_sum_mm: Optional[float]
    windspeed_max_kmh: Optional[float]

    derived_tags: List[str]


def _duesseldorf_coords() -> tuple[float, float]:
    # Düsseldorf city center – good enough for Volksgarten/Südpark selection logic
    return 51.2277, 6.7735


def derive_weather_tags(
    temperature_max_c: Optional[float],
    precipitation_probability_max: Optional[float],
    precipitation_sum_mm: Optional[float],
    windspeed_max_kmh: Optional[float],
) -> List[str]:
    tags: List[str] = []

    if (
        precipitation_probability_max is not None
        and precipitation_probability_max >= 40
    ):
        tags.append("Regen")
    if (
        precipitation_sum_mm is not None
        and precipitation_sum_mm >= 0.5
        and "Regen" not in tags
    ):
        tags.append("Regen")
    if windspeed_max_kmh is not None and windspeed_max_kmh >= 25:
        tags.append("Wind")
    if temperature_max_c is not None and temperature_max_c >= 27:
        tags.append("Heiß")
    if temperature_max_c is not None and temperature_max_c <= 5:
        tags.append("Kalt")

    # If nothing special: use generic “Sonne/Bewölkt” vibe.
    if not tags:
        tags.append("Bewölkt")

    return tags


def fetch_weather_for_day(
    day: date, timezone: str = DEFAULT_TIMEZONE
) -> WeatherSummary:
    """
    Fetch daily forecast from Open-Meteo for Düsseldorf.
    No API key required.

    If the request fails, we return a WeatherSummary with Nones and derived_tags=['Bewölkt'].
    """
    lat, lon = _duesseldorf_coords()

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
                "windspeed_10m_max",
            ]
        ),
        "timezone": timezone,
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        daily = data.get("daily", {})
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]
        pprob = (daily.get("precipitation_probability_max") or [None])[0]
        psum = (daily.get("precipitation_sum") or [None])[0]
        wind = (daily.get("windspeed_10m_max") or [None])[0]

        derived = derive_weather_tags(tmax, pprob, psum, wind)
        return WeatherSummary(
            day=day,
            temperature_max_c=tmax,
            temperature_min_c=tmin,
            precipitation_probability_max=pprob,
            precipitation_sum_mm=psum,
            windspeed_max_kmh=wind,
            derived_tags=derived,
        )
    except Exception:
        return WeatherSummary(
            day=day,
            temperature_max_c=None,
            temperature_min_c=None,
            precipitation_probability_max=None,
            precipitation_sum_mm=None,
            windspeed_max_kmh=None,
            derived_tags=["Bewölkt"],
        )
