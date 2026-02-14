# src/mikroabenteuer/recommender.py
from __future__ import annotations

import hashlib
import random
from typing import List, Optional, Tuple

from .constants import THEMES
from .models import ActivitySearchCriteria, DevelopmentDomain, MicroAdventure
from .weather import WeatherSummary


def _seed_int(*parts: str) -> int:
    s = "|".join(parts)
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _theme_match_tags(theme_key: str) -> List[str]:
    for t in THEMES:
        if t.key == theme_key:
            return t.match_tags
    return []


def matches_topics(adventure: MicroAdventure, topics: List[str]) -> bool:
    if not topics:
        return True
    adv_signals = (
        set(adventure.tags)
        | set(adventure.weather_tags)
        | set(adventure.mood_tags)
        | set(adventure.season_tags)
    )
    for topic_key in topics:
        wanted = _theme_match_tags(topic_key)
        if any(tag in adv_signals for tag in wanted):
            return True
    return False


def filter_adventures(
    adventures: List[MicroAdventure],
    criteria: ActivitySearchCriteria,
) -> List[MicroAdventure]:
    results: List[MicroAdventure] = []
    for a in adventures:
        # time filter
        if a.duration_minutes > criteria.available_minutes:
            continue

        # effort filter: gentle gating
        if criteria.effort == "niedrig":
            if a.energy_level == "hoch":
                continue
            if a.difficulty in {"mittel", "anspruchsvoll"}:
                continue
        elif criteria.effort == "mittel":
            if a.difficulty == "anspruchsvoll":
                continue

        # topics
        if not matches_topics(a, criteria.topics):
            continue

        results.append(a)
    return results


def _goal_signals(goal: DevelopmentDomain) -> set[str]:
    signals: dict[DevelopmentDomain, set[str]] = {
        DevelopmentDomain.gross_motor: {
            "Grobmotorik",
            "Bewegung",
            "Koordination",
            "Körpergefühl",
        },
        DevelopmentDomain.fine_motor: {
            "Feinmotorik",
            "Hand-Auge",
            "Greifen",
            "Sortieren",
        },
        DevelopmentDomain.language: {"Sprache", "Wortschatz", "Erzählen", "Hypothesen"},
        DevelopmentDomain.social_emotional: {
            "Empathie",
            "Teamwork",
            "Sozial",
            "Respekt",
            "Bindung",
        },
        DevelopmentDomain.sensory: {"Sensorik", "Achtsamkeit", "Wahrnehmung"},
        DevelopmentDomain.cognitive: {
            "Kategorisieren",
            "Gedächtnis",
            "Vergleich",
            "Ursache/Wirkung",
        },
    }
    return signals[goal]


def score_adventure(
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
) -> float:
    score = 0.0

    # Prefer Volksgarten slightly (requested focus)
    if "Volksgarten" in (adventure.area or ""):
        score += 1.5

    # Themes -> score boost per match
    if criteria.topics:
        adv_signals = (
            set(adventure.tags)
            | set(adventure.weather_tags)
            | set(adventure.mood_tags)
            | set(adventure.season_tags)
        )
        for topic_key in criteria.topics:
            wanted = _theme_match_tags(topic_key)
            if any(tag in adv_signals for tag in wanted):
                score += 1.0

    # Weather -> prefer matching weather_tags
    if weather:
        for wt in weather.derived_tags:
            if wt in adventure.weather_tags:
                score += 1.25
        # If rainy: avoid high “safety”/slip combos unless explicitly wanted
        if "Regen" in weather.derived_tags and adventure.safety_level == "erhöht":
            score -= 0.25

    # Effort alignment
    if criteria.effort == "niedrig":
        if adventure.energy_level == "niedrig":
            score += 0.5
        if adventure.difficulty == "leicht":
            score += 0.5
    elif criteria.effort == "hoch":
        if adventure.energy_level == "hoch":
            score += 0.5
        if adventure.difficulty in {"mittel", "anspruchsvoll"}:
            score += 0.25

    # goal alignment
    benefit_signals = (
        set(adventure.toddler_benefits) | set(adventure.tags) | set(adventure.mood_tags)
    )
    for goal in criteria.goals:
        if any(signal in benefit_signals for signal in _goal_signals(goal)):
            score += 1.0

    # safety preference (implicit: lower safety_level is easier with toddlers)
    if adventure.safety_level == "niedrig":
        score += 0.2

    return score


def pick_daily_adventure(
    adventures: List[MicroAdventure],
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary] = None,
) -> Tuple[MicroAdventure, List[MicroAdventure]]:
    """
    Deterministic daily pick (stable for the same date + criteria).
    Returns (picked, candidates_used).
    """
    candidates = filter_adventures(adventures, criteria)
    if not candidates:
        candidates = adventures[:]  # fallback: don't block the day

    scored = [(a, score_adventure(a, criteria, weather)) for a in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Take top N to keep it varied but still relevant
    top_n = max(3, min(8, len(scored)))
    top = [a for a, _ in scored[:top_n]]

    rng = random.Random(
        _seed_int(
            criteria.date.isoformat(),
            criteria.plz,
            str(criteria.radius_km),
            criteria.effort,
        )
    )
    picked = rng.choice(top)

    return picked, candidates
