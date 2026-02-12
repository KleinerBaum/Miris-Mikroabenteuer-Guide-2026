# src/mikroabenteuer/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as dt_date, datetime, time
from enum import Enum
from typing import List, Literal

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

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
    season_tags: List[str] = field(
        default_factory=list
    )  # Frühling/Sommer/Herbst/Winter
    weather_tags: List[str] = field(default_factory=list)  # Sonne/Regen/Wind/...
    energy_level: str = "mittel"  # niedrig | mittel | hoch
    difficulty: str = "leicht"  # leicht | mittel | anspruchsvoll
    age_min: float = 2.0
    age_max: float = 6.0
    mood_tags: List[str] = field(
        default_factory=list
    )  # ruhig | wild | kreativ | neugierig | sozial | fokussiert | entspannend
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

TOPICS_MAX_ITEMS = 8


class TimeWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: time
    end: time

    @model_validator(mode="after")
    def validate_time_order(self) -> "TimeWindow":
        if self.end <= self.start:
            raise ValueError("time_window.end must be after time_window.start")
        return self


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

    model_config = ConfigDict(extra="forbid")

    plz: str = Field(
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
    date: dt_date = Field(
        default_factory=dt_date.today, description="Date of the planned activity."
    )
    time_window: TimeWindow
    effort: Effort = Field(default="mittel", description="Effort level.")
    budget_eur_max: float = Field(
        default=15.0,
        ge=0.0,
        le=250.0,
        description="Budget upper bound in EUR.",
    )
    topics: List[str] = Field(default_factory=list, description="Topic keys.")
    max_suggestions: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of returned suggestions.",
    )

    @field_validator("plz")
    @classmethod
    def validate_plz(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) != 5 or not v.isdigit():
            raise ValueError("plz must contain exactly 5 digits")
        return v

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, v: List[str]) -> List[str]:
        cleaned: List[str] = []
        seen: set[str] = set()
        for item in v:
            k = (item or "").strip().lower()
            if not k:
                continue
            if k in seen:
                continue
            cleaned.append(k)
            seen.add(k)
        if len(cleaned) > TOPICS_MAX_ITEMS:
            raise ValueError(f"topics supports at most {TOPICS_MAX_ITEMS} entries")
        return cleaned

    @field_validator("effort")
    @classmethod
    def validate_effort(cls, v: str) -> str:
        if v not in set(EFFORT_LEVELS):
            raise ValueError(f"effort must be one of: {EFFORT_LEVELS}")
        return v

    @property
    def start_time(self) -> time:
        return self.time_window.start

    @property
    def end_time(self) -> time:
        return self.time_window.end

    @property
    def available_minutes(self) -> int:
        start_dt = datetime.combine(self.date, self.time_window.start)
        end_dt = datetime.combine(self.date, self.time_window.end)
        return int((end_dt - start_dt).total_seconds() // 60)

    def to_llm_params(self) -> dict[str, str | float | int | List[str]]:
        return {
            "plz": self.plz,
            "radius_km": self.radius_km,
            "date": self.date.isoformat(),
            "time_start": self.start_time.strftime("%H:%M"),
            "time_end": self.end_time.strftime("%H:%M"),
            "effort": self.effort,
            "budget_eur_max": self.budget_eur_max,
            "topics": self.topics,
            "max_suggestions": self.max_suggestions,
        }


class WeatherCondition(str, Enum):
    sunny = "sunny"
    cloudy = "cloudy"
    rainy = "rainy"
    stormy = "stormy"
    snowy = "snowy"
    foggy = "foggy"
    unknown = "unknown"


class IndoorOutdoor(str, Enum):
    indoor = "indoor"
    outdoor = "outdoor"
    mixed = "mixed"


class WeatherSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: WeatherCondition
    summary_de_en: str
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_probability_pct: int | None = None
    precipitation_sum_mm: float | None = None
    wind_speed_max_kmh: float | None = None
    country_code: str | None = None
    city: str | None = None
    region: str | None = None
    timezone: str | None = None
    data_source: str | None = None


class SearchStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indoor_bias: float = Field(ge=0.0, le=1.0)
    outdoor_bias: float = Field(ge=0.0, le=1.0)
    rationale_de_en: str
    query_hints: List[str] = Field(default_factory=list)


class ActivitySuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    reason_de_en: str
    date: dt_date
    start_time: time | None = None
    distance_km: float | None = None
    expected_cost_eur: float | None = None
    indoor_outdoor: IndoorOutdoor = IndoorOutdoor.mixed
    source_urls: List[AnyUrl] = Field(default_factory=list)


class ActivitySuggestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weather: WeatherSummary | None = None
    suggestions: List[ActivitySuggestion] = Field(default_factory=list)
    sources: List[AnyUrl] = Field(default_factory=list)
    warnings_de_en: List[str] = Field(default_factory=list)
    errors_de_en: List[str] = Field(default_factory=list)
