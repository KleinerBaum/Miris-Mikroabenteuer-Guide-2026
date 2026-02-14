from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import ActivitySearchCriteria, ActivitySuggestion, IndoorOutdoor


class ActivityLibraryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    domain_tags: list[str] = Field(default_factory=list)
    age_min_years: float = Field(ge=0.0, le=18.0)
    age_max_years: float = Field(ge=0.0, le=18.0)
    indoor_outdoor: IndoorOutdoor
    duration_min: int = Field(ge=15, le=360)
    materials: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    effort: str = Field(default="mittel")
    estimated_cost_eur: float = Field(default=0.0, ge=0.0, le=250.0)


def _activity_library_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "activity_library.json"


def load_activity_library() -> list[ActivityLibraryItem]:
    data_path = _activity_library_path()
    raw_payload = json.loads(data_path.read_text(encoding="utf-8"))
    items_raw = (
        raw_payload.get("activities", []) if isinstance(raw_payload, dict) else []
    )
    return [ActivityLibraryItem.model_validate(item) for item in items_raw]


def _score_item(
    item: ActivityLibraryItem,
    criteria: ActivitySearchCriteria,
    *,
    child_age_years: float,
) -> float:
    score = 0.0

    if item.age_min_years <= child_age_years <= item.age_max_years:
        score += 3.0
    else:
        score -= 4.0

    if item.duration_min <= criteria.available_minutes:
        score += 1.5

    if item.estimated_cost_eur <= criteria.budget_eur_max:
        score += 1.5
    else:
        score -= 2.0

    if item.effort == criteria.effort:
        score += 1.0

    if criteria.location_preference == item.indoor_outdoor.value:
        score += 1.0
    elif criteria.location_preference == "mixed":
        score += 0.3

    topic_overlap = set(criteria.topics).intersection(set(item.domain_tags))
    score += min(2.0, 0.6 * len(topic_overlap))

    preferred_materials = _extract_material_preferences(criteria)
    if preferred_materials:
        item_materials_normalized = {
            _normalize_text(material) for material in item.materials
        }
        material_matches = preferred_materials.intersection(item_materials_normalized)
        if material_matches:
            score += min(2.0, 0.8 * len(material_matches))
        else:
            score -= 1.5

    # Prefer shorter activities when multiple options fit the time window.
    if criteria.available_minutes > 0:
        duration_ratio = item.duration_min / criteria.available_minutes
        score += max(0.0, 1.0 - duration_ratio)

    return score


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _extract_material_preferences(criteria: ActivitySearchCriteria) -> set[str]:
    preferences: set[str] = set()
    for constraint in criteria.constraints:
        cleaned = _normalize_text(constraint)
        if not cleaned:
            continue
        if cleaned.startswith("material:"):
            material = cleaned.split(":", maxsplit=1)[1].strip()
            if material:
                preferences.add(material)
    return preferences


def _is_filtered_out(
    item: ActivityLibraryItem,
    criteria: ActivitySearchCriteria,
    *,
    child_age_years: float,
) -> bool:
    if not (item.age_min_years <= child_age_years <= item.age_max_years):
        return True
    if item.duration_min > criteria.available_minutes:
        return True
    return False


def suggest_activities_offline(
    criteria: ActivitySearchCriteria,
    *,
    child_age_years: float = 6.0,
) -> tuple[list[ActivitySuggestion], list[str]]:
    items = load_activity_library()
    filtered_items = [
        item
        for item in items
        if not _is_filtered_out(item, criteria, child_age_years=child_age_years)
    ]

    scored = sorted(
        filtered_items,
        key=lambda item: _score_item(item, criteria, child_age_years=child_age_years),
        reverse=True,
    )

    suggestions: list[ActivitySuggestion] = []
    warnings: list[str] = []

    for item in scored:
        if len(suggestions) >= criteria.max_suggestions:
            break
        reason_payload: dict[str, Any] = {
            "library_id": item.id,
            "age": f"{item.age_min_years}-{item.age_max_years}",
            "duration_min": item.duration_min,
            "domain_tags": item.domain_tags,
            "materials": item.materials,
            "safety_notes": item.safety_notes,
        }
        suggestions.append(
            ActivitySuggestion(
                title=item.title,
                date=criteria.date,
                start_time=criteria.start_time,
                end_time=criteria.end_time,
                location="Offline Activity Library",
                expected_cost_eur=item.estimated_cost_eur,
                indoor_outdoor=item.indoor_outdoor,
                description=item.description,
                reason_de_en=(
                    "Offline-Bibliothek Treffer / Offline library match: "
                    + json.dumps(reason_payload, ensure_ascii=False)
                ),
                source_urls=[],
            )
        )

    if not suggestions:
        warnings.append(
            "Keine Offline-Treffer gefunden. Bitte Budget/Zeit/Topics anpassen. / No offline matches found."
        )

    return suggestions, warnings
