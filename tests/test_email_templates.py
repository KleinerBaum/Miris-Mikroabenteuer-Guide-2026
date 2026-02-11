from __future__ import annotations

from mikroabenteuer.email_templates import build_html_mail
from mikroabenteuer.models import Adventure, SafetyProfile


def test_build_html_mail_renders_bilingual_sections() -> None:
    adventure = Adventure(
        id="a1",
        title="Wolkenkino",
        location="Volksgarten",
        duration="45 Minuten",
        intro_quote="Los geht's",
        description="Beschreibung",
        preparation=["Vorbereitung"],
        steps=["Schritt"],
        child_benefit="Gut für Kreativität",
        carla_tip="Warme Jacke",
        safety=SafetyProfile(risks=["Nässe"], prevention=["Regenjacke"]),
    )

    html = build_html_mail(adventure)

    assert "Daily adventure / Tagesabenteuer" in html
    assert "Ort / Location" in html
    assert "Nässe" in html
