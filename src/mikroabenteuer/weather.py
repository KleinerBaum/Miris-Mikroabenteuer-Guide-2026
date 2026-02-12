# src/mikroabenteuer/weather.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

import requests

from .constants import DEFAULT_TIMEZONE


@dataclass(frozen=True)
class WeatherSummary:
    day: date
    condition: str = "unknown"
    summary_de_en: str = "Unbekannt / Unknown"
    temperature_max_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    precipitation_probability_pct: Optional[float] = None
    precipitation_sum_mm: Optional[float] = None
    wind_speed_max_kmh: Optional[float] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    timezone: Optional[str] = None
    data_source: Optional[str] = None
    derived_tags: List[str] = field(default_factory=lambda: ["Bewölkt"])

    @property
    def precipitation_probability_max(self) -> Optional[float]:
        return self.precipitation_probability_pct

    @property
    def windspeed_max_kmh(self) -> Optional[float]:
        return self.wind_speed_max_kmh


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
            condition="unknown",
            summary_de_en="Bewölkt / Cloudy",
            temperature_max_c=tmax,
            temperature_min_c=tmin,
            precipitation_probability_pct=pprob,
            precipitation_sum_mm=psum,
            wind_speed_max_kmh=wind,
            country_code="DE",
            timezone=timezone,
            data_source="open-meteo",
            derived_tags=derived,
        )
    except Exception:
        return WeatherSummary(
            day=day,
            condition="unknown",
            summary_de_en="Bewölkt / Cloudy",
            temperature_max_c=None,
            temperature_min_c=None,
            precipitation_probability_pct=None,
            precipitation_sum_mm=None,
            wind_speed_max_kmh=None,
            country_code="DE",
            timezone=timezone,
            data_source="open-meteo",
            derived_tags=["Bewölkt"],
        )
