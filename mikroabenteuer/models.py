from __future__ import annotations

from datetime import date, time
from enum import Enum
from typing import List

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class SafetyProfile(BaseModel):
    risks: List[str]
    prevention: List[str]


class Adventure(BaseModel):
    id: str
    title: str
    location: str
    duration: str
    intro_quote: str
    description: str
    preparation: List[str]
    steps: List[str]
    child_benefit: str
    carla_tip: str
    safety: SafetyProfile


# -----------------------------------------------------------------------------
# Activity Search (NEW)
# -----------------------------------------------------------------------------

PLZ_LENGTH = 5
RADIUS_KM_MIN = 0.5
RADIUS_KM_MAX = 50.0
BUDGET_EUR_MIN = 0.0
BUDGET_EUR_MAX = 500.0
TOPICS_MAX_ITEMS = 8
SOURCE_URLS_MIN_ITEMS = 1
SOURCE_URLS_MAX_ITEMS = 10
SUGGESTIONS_MIN_ITEMS = 1
SUGGESTIONS_MAX_ITEMS = 5


class EffortLevel(str, Enum):
    LOW = "niedrig"
    MEDIUM = "mittel"
    HIGH = "hoch"


class WeatherCondition(str, Enum):
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    STORMY = "stormy"
    SNOWY = "snowy"


class SearchStrategy(str, Enum):
    BALANCED = "balanced"
    WEATHER_FIRST = "weather_first"
    BUDGET_FIRST = "budget_first"
    NEARBY_FIRST = "nearby_first"


class TimeWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: time
    end: time

    @model_validator(mode="after")
    def validate_window_order(self) -> TimeWindow:
        if self.end <= self.start:
            raise ValueError("time_window.end must be after time_window.start")
        return self


class ActivitySearchCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plz: str = Field(min_length=PLZ_LENGTH, max_length=PLZ_LENGTH)
    radius_km: float = Field(ge=RADIUS_KM_MIN, le=RADIUS_KM_MAX)
    date: date
    time_window: TimeWindow
    effort: EffortLevel
    budget_eur_max: float = Field(ge=BUDGET_EUR_MIN, le=BUDGET_EUR_MAX)
    topics: List[str] = Field(default_factory=list, max_length=TOPICS_MAX_ITEMS)

    @field_validator("plz")
    @classmethod
    def validate_plz(cls, value: str) -> str:
        plz = value.strip()
        if len(plz) != PLZ_LENGTH or not plz.isdigit():
            raise ValueError("plz must contain exactly 5 digits")
        return plz

    @field_validator("topics")
    @classmethod
    def normalize_topics(cls, value: List[str]) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()

        for item in value:
            topic = item.strip().lower()
            if not topic or topic in seen:
                continue
            normalized.append(topic)
            seen.add(topic)

        if len(normalized) > TOPICS_MAX_ITEMS:
            raise ValueError(f"topics supports at most {TOPICS_MAX_ITEMS} entries")
        return normalized


class WeatherReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    condition: WeatherCondition
    temperature_c: float = Field(ge=-40.0, le=55.0)
    precipitation_probability: float = Field(ge=0.0, le=1.0)


class ActivitySuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_urls: List[AnyUrl] = Field(
        min_length=SOURCE_URLS_MIN_ITEMS,
        max_length=SOURCE_URLS_MAX_ITEMS,
    )


class ActivityPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: ActivitySearchCriteria
    weather: WeatherReport
    strategy: SearchStrategy
    suggestions: List[ActivitySuggestion] = Field(
        min_length=SUGGESTIONS_MIN_ITEMS,
        max_length=SUGGESTIONS_MAX_ITEMS,
    )
