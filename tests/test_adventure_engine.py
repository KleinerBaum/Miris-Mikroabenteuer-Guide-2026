from __future__ import annotations

from mikroabenteuer.adventure_engine import choose_adventure
from mikroabenteuer.models import Adventure, SafetyProfile


def _build_adventure(title: str, location: str) -> Adventure:
    return Adventure(
        id=title,
        title=title,
        location=location,
        duration="60 Minuten",
        intro_quote="Zitat",
        description="Beschreibung",
        preparation=["Vorbereitung"],
        steps=["Schritt"],
        child_benefit="Benefit",
        carla_tip="Tipp",
        safety=SafetyProfile(risks=["Risk"], prevention=["Prevent"]),
    )


def test_choose_adventure_prefers_rain(monkeypatch) -> None:
    adventures = [
        _build_adventure("Sonnenabenteuer", "Wiese"),
        _build_adventure("Waldabenteuer", "Wald"),
    ]
    monkeypatch.setattr(
        "mikroabenteuer.adventure_engine.load_adventures", lambda: adventures
    )
    monkeypatch.setattr(
        "mikroabenteuer.adventure_engine.get_weather",
        lambda: {"rain": 1.0, "temperature": 21.0, "wind": 5.0},
    )

    selected = choose_adventure()

    assert selected.title == "Waldabenteuer"


def test_choose_adventure_defaults_to_first(monkeypatch) -> None:
    adventures = [_build_adventure("Fallback", "Irgendwo")]
    monkeypatch.setattr(
        "mikroabenteuer.adventure_engine.load_adventures", lambda: adventures
    )
    monkeypatch.setattr(
        "mikroabenteuer.adventure_engine.get_weather",
        lambda: {"rain": 0.0, "temperature": 14.0, "wind": 5.0},
    )

    selected = choose_adventure()

    assert selected.title == "Fallback"
