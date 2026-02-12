# src/mikroabenteuer/constants.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

Language = Literal["DE", "EN"]

EFFORT_LEVELS: Tuple[str, ...] = ("niedrig", "mittel", "hoch")
DIFFICULTY_LEVELS: Tuple[str, ...] = ("leicht", "mittel", "anspruchsvoll")
SAFETY_LEVELS: Tuple[str, ...] = ("niedrig", "mittel", "erhöht")

SEASON_TAGS: Tuple[str, ...] = ("Frühling", "Sommer", "Herbst", "Winter")
WEATHER_TAGS: Tuple[str, ...] = ("Sonne", "Bewölkt", "Regen", "Wind", "Kalt", "Heiß")

DEFAULT_TIMEZONE = "Europe/Berlin"
DEFAULT_CITY = "Düsseldorf"
DEFAULT_AREA = "Volksgarten / Südpark"


@dataclass(frozen=True)
class Theme:
    key: str
    labels: Dict[Language, str]
    # Tags/Signals used to match this theme against an adventure
    match_tags: List[str]


THEMES: List[Theme] = [
    Theme("nature", {"DE": "Natur", "EN": "Nature"}, ["Natur"]),
    Theme(
        "movement",
        {"DE": "Bewegung", "EN": "Movement"},
        ["Bewegung", "Motorik", "Abenteuer"],
    ),
    Theme(
        "creative", {"DE": "Kreativ", "EN": "Creative"}, ["Kreativ", "Musik", "Sprache"]
    ),
    Theme("learning", {"DE": "Lernen", "EN": "Learning"}, ["Lernen"]),
    Theme(
        "mindfulness",
        {"DE": "Achtsamkeit", "EN": "Mindfulness"},
        ["Achtsamkeit", "Ruhig"],
    ),
    Theme(
        "social",
        {"DE": "Sozial", "EN": "Social"},
        ["Sozial", "Werte", "Bonding", "Alltag"],
    ),
    Theme("water", {"DE": "Wasser", "EN": "Water"}, ["Wasser"]),
    Theme("rain", {"DE": "Regen", "EN": "Rain"}, ["Regen"]),
    Theme("wind", {"DE": "Wind", "EN": "Wind"}, ["Wind"]),
    Theme("winter", {"DE": "Winter", "EN": "Winter"}, ["Winter"]),
    Theme("evening", {"DE": "Abend", "EN": "Evening"}, ["Abend"]),
    Theme("playground", {"DE": "Spielplatz", "EN": "Playground"}, ["Spielplatz"]),
]


def theme_options(lang: Language) -> List[str]:
    """Return theme keys in stable order."""
    return [t.key for t in THEMES]


def theme_label(theme_key: str, lang: Language) -> str:
    for t in THEMES:
        if t.key == theme_key:
            return t.labels[lang]
    return theme_key


def effort_label(effort_key: str, lang: Language) -> str:
    labels = {
        "niedrig": {"DE": "niedrig (easy)", "EN": "low (easy)"},
        "mittel": {"DE": "mittel (normal)", "EN": "medium (normal)"},
        "hoch": {"DE": "hoch (sporty)", "EN": "high (sporty)"},
    }
    return labels.get(effort_key, {}).get(lang, effort_key)
