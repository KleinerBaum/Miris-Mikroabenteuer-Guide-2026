from __future__ import annotations

from collections.abc import Iterable

from mikroabenteuer.data_loader import load_adventures
from mikroabenteuer.models import Adventure
from mikroabenteuer.weather_service import get_weather


def _first_matching(
    adventures: Iterable[Adventure], *keywords: str
) -> Adventure | None:
    for adventure in adventures:
        haystack = f"{adventure.title} {adventure.location}".lower()
        if any(keyword.lower() in haystack for keyword in keywords):
            return adventure

    return None


def choose_adventure() -> Adventure:
    """Pick an adventure based on current weather in Düsseldorf."""
    adventures = load_adventures()
    weather = get_weather()

    if weather["rain"] > 0:
        match = _first_matching(adventures, "wald", "bäume", "natur")
        if match:
            return match

    if weather["temperature"] > 20:
        match = _first_matching(adventures, "wiese", "see", "picknick")
        if match:
            return match

    if weather["wind"] > 20:
        match = _first_matching(adventures, "wolken", "drachen", "wind")
        if match:
            return match

    if weather["temperature"] < 10:
        match = _first_matching(adventures, "spielplatz", "bewegung", "lauf")
        if match:
            return match

    return adventures[0]
