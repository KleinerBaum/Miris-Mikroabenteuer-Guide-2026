# mikroabenteuer/activity_orchestrator.py
from __future__ import annotations

from datetime import date as date_t
from typing import Callable, Literal

import httpx  # type: ignore[import-not-found]

from .models import (
    ActivitySearchCriteria,
    ActivitySuggestion,
    ActivitySuggestionResult,
    SearchStrategy,
    WeatherCondition,
    WeatherSummary,
)
from .openai_activity_service import suggest_activities

from mikroabenteuer.retry import retry_with_backoff


ProgressCb = Callable[[str], None]


def _progress(cb: ProgressCb | None, msg: str) -> None:
    if cb:
        cb(msg)


def _weather_condition_from_open_meteo_code(code: int | None) -> WeatherCondition:
    if code is None:
        return WeatherCondition.unknown
    # Open-Meteo weather codes mapping (simplified)
    if code == 0:
        return WeatherCondition.sunny
    if code in (1, 2, 3):
        return WeatherCondition.cloudy
    if code in (45, 48):
        return WeatherCondition.foggy
    if 51 <= code <= 67 or 80 <= code <= 82:
        return WeatherCondition.rainy
    if 71 <= code <= 77 or 85 <= code <= 86:
        return WeatherCondition.snowy
    if code >= 95:
        return WeatherCondition.stormy
    return WeatherCondition.unknown


def _build_strategy(weather: WeatherSummary) -> SearchStrategy:
    # Basic weather-dependent bias
    if weather.condition in (
        WeatherCondition.rainy,
        WeatherCondition.stormy,
        WeatherCondition.snowy,
    ):
        return SearchStrategy(
            indoor_bias=0.8,
            outdoor_bias=0.2,
            rationale_de_en="Regen/Unwetter → mehr Indoor / Rain/storm → prefer indoor",
            query_hints=["indoor", "museum", "ausstellung", "kino", "café", "workshop"],
        )
    if weather.condition in (
        WeatherCondition.sunny,
        WeatherCondition.cloudy,
        WeatherCondition.foggy,
    ):
        return SearchStrategy(
            indoor_bias=0.35,
            outdoor_bias=0.65,
            rationale_de_en="Okayes Wetter → mehr Outdoor / decent weather → prefer outdoor",
            query_hints=[
                "outdoor",
                "wanderung",
                "spaziergang",
                "park",
                "aussichtspunkt",
                "radtour",
            ],
        )
    return SearchStrategy(
        indoor_bias=0.5,
        outdoor_bias=0.5,
        rationale_de_en="Wetter unklar → neutral / unknown weather → neutral",
        query_hints=["indoor", "outdoor", "veranstaltung", "event"],
    )


def _get_lat_lon_for_de_postal_code(
    plz: str, *, timeout_s: float = 6.0
) -> tuple[float, float, str | None, str | None]:
    """
    Geocode via Zippopotam: https://api.zippopotam.us/de/{plz}
    Returns (lat, lon, city, region/state).
    """
    url = f"https://api.zippopotam.us/de/{plz}"
    with httpx.Client(timeout=timeout_s) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()

    places = data.get("places") or []
    if not places:
        raise RuntimeError("No places found for postal code.")
    p0 = places[0]
    lat = float(p0["latitude"])
    lon = float(p0["longitude"])
    city = p0.get("place name")
    region = p0.get("state")
    return lat, lon, city, region


def _fetch_open_meteo_daily(
    lat: float, lon: float, target_date: date_t, *, timeout_s: float = 8.0
) -> dict:
    """
    Uses Open-Meteo daily forecast when possible, else archive for past.
    Forecast horizon is limited; if date is too far in the future, it may fail.
    """
    today = date_t.today()
    is_past = target_date < today

    # Open-Meteo endpoints
    base = (
        "https://archive-api.open-meteo.com/v1/archive"
        if is_past
        else "https://api.open-meteo.com/v1/forecast"
    )

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
            ]
        ),
        "timezone": "Europe/Berlin",
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
    }

    with httpx.Client(timeout=timeout_s) as client:
        r = client.get(base, params=params)
        r.raise_for_status()
        return r.json()


def get_weather_summary(
    criteria: ActivitySearchCriteria, *, progress_cb: ProgressCb | None = None
) -> WeatherSummary:
    _progress(progress_cb, "Wetter abrufen … / Fetching weather …")

    def _call() -> WeatherSummary:
        lat, lon, city, region = _get_lat_lon_for_de_postal_code(criteria.plz)
        raw = _fetch_open_meteo_daily(lat, lon, criteria.date)

        daily = raw.get("daily") or {}
        # arrays of length 1 because start_date=end_date
        code = (daily.get("weather_code") or [None])[0]
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]
        p_sum = (daily.get("precipitation_sum") or [None])[0]
        p_prob = (daily.get("precipitation_probability_max") or [None])[0]
        wind = (daily.get("wind_speed_10m_max") or [None])[0]

        cond = _weather_condition_from_open_meteo_code(code)
        summary = {
            WeatherCondition.sunny: "Sonnig / Sunny",
            WeatherCondition.cloudy: "Bewölkt / Cloudy",
            WeatherCondition.rainy: "Regen / Rain",
            WeatherCondition.snowy: "Schnee / Snow",
            WeatherCondition.stormy: "Gewitter/Sturm / Storm",
            WeatherCondition.foggy: "Nebel / Fog",
            WeatherCondition.unknown: "Unbekannt / Unknown",
        }[cond]

        return WeatherSummary(
            condition=cond,
            summary_de_en=summary,
            temperature_min_c=float(tmin) if tmin is not None else None,
            temperature_max_c=float(tmax) if tmax is not None else None,
            precipitation_probability_pct=int(p_prob) if p_prob is not None else None,
            precipitation_sum_mm=float(p_sum) if p_sum is not None else None,
            wind_speed_max_kmh=float(wind) if wind is not None else None,
            country_code="DE",
            city=city,
            region=region,
            timezone="Europe/Berlin",
            data_source="open-meteo",
        )

    return retry_with_backoff(max_attempts=3, base_delay=0.5)(_call)()


def _score_suggestion(
    s: ActivitySuggestion,
    criteria: ActivitySearchCriteria,
    strategy: SearchStrategy,
) -> float:
    score = 0.0

    # Distance
    if s.distance_km is not None:
        if s.distance_km <= criteria.radius_km:
            score += 2.0
            # closer = better
            score += max(0.0, 1.0 - (s.distance_km / max(1.0, criteria.radius_km)))
        else:
            score -= 2.0

    # Budget
    if s.expected_cost_eur is not None:
        score += 1.5 if s.expected_cost_eur <= criteria.budget_eur_max else -2.0

    # Indoor/outdoor bias
    if s.indoor_outdoor.value == "indoor":
        score += 2.0 * strategy.indoor_bias
    elif s.indoor_outdoor.value == "outdoor":
        score += 2.0 * strategy.outdoor_bias
    else:
        score += 1.0  # mixed

    # Themes match (heuristic: look for theme codes in reason/title)
    blob = (s.title + " " + s.reason_de_en).lower()
    for t in criteria.topics:
        if t in blob:
            score += 0.3

    return score


def prioritize_suggestions(
    suggestions: list[ActivitySuggestion],
    criteria: ActivitySearchCriteria,
    strategy: SearchStrategy,
) -> list[ActivitySuggestion]:
    # De-dup (title + date + start_time)
    seen = set()
    uniq: list[ActivitySuggestion] = []
    for s in suggestions:
        key = (
            s.title.strip().lower(),
            s.date.isoformat(),
            getattr(s.start_time, "isoformat", lambda: None)(),
        )
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)

    scored = sorted(
        uniq,
        key=lambda x: _score_suggestion(x, criteria, strategy),
        reverse=True,
    )

    return scored[: criteria.max_suggestions]


def orchestrate_activity_search(
    criteria: ActivitySearchCriteria,
    mode: Literal["schnell", "genau"],
    *,
    base_url: str | None = None,
    progress_cb: ProgressCb | None = None,
) -> ActivitySuggestionResult:
    warnings: list[str] = []
    errors: list[str] = []

    # 1) Weather
    try:
        weather = get_weather_summary(criteria, progress_cb=progress_cb)
    except Exception as e:
        weather = WeatherSummary(
            condition=WeatherCondition.unknown,
            summary_de_en="Wetter konnte nicht geladen werden / Weather fetch failed",
            data_source=None,
        )
        warnings.append(f"Wetter: Fehler / Weather error: {type(e).__name__}: {e}")

    # 2) Strategy
    strategy = _build_strategy(weather)
    _progress(progress_cb, f"Strategie: {strategy.rationale_de_en}")

    # 3) OpenAI WebSearch call
    _progress(progress_cb, "Events suchen … / Searching events …")
    try:
        result = suggest_activities(
            criteria,
            mode,
            base_url=base_url,
            weather=weather,
            strategy=strategy,
        )
    except Exception as e:
        errors.append(f"OpenAI: Fehler / Error: {type(e).__name__}: {e}")
        return ActivitySuggestionResult(
            weather=weather,
            suggestions=[],
            sources=[],
            warnings_de_en=warnings,
            errors_de_en=errors,
        )

    # 4) Prioritize + enforce deterministic weather
    result.weather = weather
    result.warnings_de_en = list(
        dict.fromkeys((result.warnings_de_en or []) + warnings)
    )
    result.errors_de_en = list(dict.fromkeys((result.errors_de_en or []) + errors))
    result.suggestions = prioritize_suggestions(result.suggestions, criteria, strategy)

    # flatten sources
    src = []
    for s in result.suggestions:
        src.extend(list(s.source_urls))
    # unique keep order
    out = []
    seen = set()
    for u in src:
        if str(u) not in seen:
            out.append(u)
            seen.add(str(u))
    result.sources = out[:30]

    if not result.suggestions:
        result.warnings_de_en.append(
            "Keine Treffer / No results. Radius/Topics/Budget prüfen."
        )

    _progress(progress_cb, "Fertig / Done")
    return result
