from __future__ import annotations

import re
from typing import Iterable

COMMON_HOUSEHOLD_MATERIALS: tuple[str, ...] = (
    "paper",
    "pens",
    "tape",
    "scissors",
    "bowls",
    "rice",
    "flashlight",
)

MATERIAL_LABELS: dict[str, str] = {
    "paper": "Papier / Paper",
    "pens": "Stifte / Pens",
    "tape": "Klebeband / Tape",
    "scissors": "Kinderschere / Safety scissors",
    "bowls": "Schüsseln / Bowls",
    "rice": "Reis / Rice",
    "flashlight": "Taschenlampe / Flashlight",
}

MATERIAL_ALIASES: dict[str, tuple[str, ...]] = {
    "paper": ("papier", "paper", "zettel", "blatt", "vorlage", "notizbuch"),
    "pens": ("stift", "stifte", "marker", "kreide", "pens", "pen"),
    "tape": ("klebeband", "tape"),
    "scissors": ("schere", "scissors"),
    "bowls": ("schüssel", "schuessel", "bowls", "bowl"),
    "rice": ("reis", "rice"),
    "flashlight": ("taschenlampe", "flashlight", "lampe"),
}

SUBSTITUTIONS: dict[str, str] = {
    "paper": "Nutze abwischbare Fläche (Fenster/Tafel) statt Papier. / Use a wipeable surface instead of paper.",
    "pens": "Nutze Fingerzeigen oder Gegenstände statt Stifte. / Use pointing or objects instead of pens.",
    "tape": "Nutze vorhandene Kanten/Linien statt Klebeband. / Use existing edges/lines instead of tape.",
    "scissors": "Kein Schneiden nötig; stattdessen reißen oder sortieren. / Skip cutting; tear or sort instead.",
    "bowls": "Nutze Becher oder kleine Dosen statt Schüsseln. / Use cups or small containers instead of bowls.",
    "rice": "Nutze trockene Bohnen/Nudeln oder Naturmaterialien statt Reis. / Use dry beans/pasta or natural items instead of rice.",
    "flashlight": "Nutze Tageslicht und Schatten statt Taschenlampe. / Use daylight and shadows instead of a flashlight.",
}


def normalize_material_token(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def blocked_materials(available_materials: Iterable[str]) -> set[str]:
    available = {normalize_material_token(item) for item in available_materials if item}
    if not available:
        return set()
    return {m for m in COMMON_HOUSEHOLD_MATERIALS if m not in available}


def material_matches_blocklist(text: str, blocked: set[str]) -> set[str]:
    normalized = normalize_material_token(text)
    hits: set[str] = set()
    for key in blocked:
        aliases = MATERIAL_ALIASES.get(key, ())
        if any(alias in normalized for alias in aliases):
            hits.add(key)
    return hits


def substitutions_for(blocked: set[str]) -> list[str]:
    return [
        SUBSTITUTIONS[item] for item in COMMON_HOUSEHOLD_MATERIALS if item in blocked
    ]
