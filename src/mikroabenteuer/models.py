# src/mikroabenteuer/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .constants import (
    DIFFICULTY_LEVELS,
    EFFORT_LEVELS,
    SAFETY_LEVELS,
    SEASON_TAGS,
    WEATHER_TAGS,
)


@dataclass
class MicroAdventure:
    slug: str
    title: str
    area: str
    short: str

    duration_minutes: int
    distance_km: float
    best_time: str
    stroller_ok: bool

    start_point: str
    route_steps: List[str]
    preparation: List[str]
    packing_list: List[str]
    execution_tips: List[str]
    variations: List[str]
    toddler_benefits: List[str]
    carla_tip: str

    risks: List[str]
    mitigations: List[str]

    tags: List[str]
    accessibility: List[str] = field(default_factory=list)

    # --- V2 fields ---
    season_tags: List[str] = field(default_factory=list)  # Frühling/Sommer/Herbst/Winter
    weather_tags: List[str] = field(default_factory=list)  # Sonne/Regen/Wind/...
    energy_level: str = "mittel"  # niedrig | mittel | hoch
    difficulty: str = "leicht"  # leicht | mittel | anspruchsvoll
    age_min: float = 2.0
    age_max: float = 6.0
    mood_tags: List[str] = field(default_factory=list)  # ruhig | wild | kreativ | neugierig | sozial | fokussiert | entspannend
    safety_level: str = "niedrig"  # niedrig | mittel | erhöht

    def validate(self) -> None:
        if not self.slug or not isinstance(self.slug, str):
            raise ValueError("MicroAdventure.slug must be a non-empty string")
        if not self.title:
            raise ValueError(f"{self.slug}: title missing")
        if self.duration_minutes <= 0:
            raise ValueError(f"{self.slug}: duration_minutes must be > 0")
        if self.distance_km < 0:
            raise ValueError(f"{self.slug}: distance_km must be >= 0")
        if self.age_min < 0 or self.age_max < 0 or self.age_min > self.age_max:
            raise ValueError(f"{self.slug}: invalid age range (age_min/age_max)")
        if self.difficulty not in set(DIFFICULTY_LEVELS):
            raise ValueError(f"{self.slug}: invalid difficulty={self.difficulty}")
        if self.safety_level not in set(SAFETY_LEVELS):
            raise ValueError(f"{self.slug}: invalid safety_level={self.safety_level}")
        if self.energy_level not in {"niedrig", "mittel", "hoch"}:
            raise ValueError(f"{self.slug}: invalid energy_level={self.energy_level}")

        # Soft validation: only validate known season/weather tags if provided
        for s in self.season_tags:
            if s not in set(SEASON_TAGS):
                raise ValueError(f"{self.slug}: unknown season_tag={s}")
        for w in self.weather_tags:
            if w not in set(WEATHER_TAGS):
                raise ValueError(f"{self.slug}: unknown weather_tag={w}")

        # Keep lists sane
        if not self.route_steps:
            raise ValueError(f"{self.slug}: route_steps must not be empty")
        if not self.toddler_benefits:
            raise ValueError(f"{self.slug}: toddler_benefits must not be empty")

    def summary_row(self) -> dict:
        return {
            "slug": self.slug,
            "title": self.title,
            "area": self.area,
            "duration_min": self.duration_minutes,
            "distance_km": self.distance_km,
            "stroller_ok": self.stroller_ok,
            "energy": self.energy_level,
            "difficulty": self.difficulty,
            "safety": self.safety_level,
        }


def ensure_unique_slugs(adventures: List[MicroAdventure]) -> None:
    seen: set[str] = set()
    dupes: List[str] = []
    for a in adventures:
        if a.slug in seen:
            dupes.append(a.slug)
        seen.add(a.slug)
    if dupes:
        raise ValueError(f"Duplicate slugs found: {sorted(set(dupes))}")


# ---------------------------------------------------------------------
# Search Criteria (Pydantic) – zentrale Validierung für Streamlit
# ---------------------------------------------------------------------
Effort = Literal["niedrig", "mittel", "hoch"]


class ActivitySearchCriteria(BaseModel):
    """
    Strukturierte Eingabe für Suchkriterien:
    - PLZ (DE) + Radius
    - Datum
    - verfügbare Zeit (Minuten)
    - Aufwand
    - Budget-Obergrenze
    - Themengebiete (Theme-Keys aus constants.THEMES)
    """

    postal_code: str = Field(
        default="40215",
        description="German postal code (PLZ), 5 digits.",
        examples=["40215", "40210"],
        min_length=5,
        max_length=5,
    )
    radius_km: float = Field(
        default=5.0,
        ge=0.5,
        le=50.0,
        description="Search radius in kilometers.",
    )
    day: date = Field(default_factory=date.today, description="Date of the planned activity.")
    available_minutes: int = Field(
        default=60,
        ge=15,
        le=360,
        description="Available time in minutes.",
    )
    effort: Effort = Field(default="mittel", description="Effort level.")
    budget_eur_max: float = Field(
        default=15.0,
        ge=0.0,
        le=250.0,
        description="Budget upper bound in EUR.",
    )
    themes: List[str] = Field(default_factory=list, description="Theme keys.")
    # Optional time window (kept optional but useful for scheduler/ICS)
    start_time: Optional[time] = Field(default=None, description="Optional preferred start time.")
    end_time: Optional[time] = Field(default=None, description="Optional preferred end time.")

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) != 5 or not v.isdigit():
            raise ValueError("postal_code must be 5 digits (e.g. 40215)")
        return v

    @field_validator("themes")
    @classmethod
    def validate_themes(cls, v: List[str]) -> List[str]:
        # Keep stable ordering + unique keys
        cleaned: List[str] = []
        seen: set[str] = set()
        for item in v:
            k = (item or "").strip()
            if not k:
                continue
            if k in seen:
                continue
            cleaned.append(k)
            seen.add(k)
        # soft limit to keep prompts small/consistent
        if len(cleaned) > 8:
            raise ValueError("too many themes selected (max 8)")
        return cleaned

    @field_validator("effort")
    @classmethod
    def validate_effort(cls, v: str) -> str:
        if v not in set(EFFORT_LEVELS):
            raise ValueError(f"effort must be one of: {EFFORT_LEVELS}")
        return v

    @field_validator("end_time")
    @classmethod
    def validate_time_window(cls, end_time_val, info):
        start_time_val = info.data.get("start_time")
        if start_time_val and end_time_val and end_time_val <= start_time_val:
            raise ValueError("end_time must be after start_time")
        return end_time_val
