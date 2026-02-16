from __future__ import annotations

from datetime import date, time

from mikroabenteuer.email_templates import render_daily_email_html
from mikroabenteuer.models import ActivitySearchCriteria, MicroAdventure, TimeWindow


def _sample_adventure() -> MicroAdventure:
    return MicroAdventure(
        slug="wolkenkino",
        title="Wolkenkino im Volksgarten",
        area="Volksgarten Düsseldorf",
        short="Wolken schauen und Geschichten erfinden",
        duration_minutes=45,
        distance_km=1.2,
        best_time="vormittags",
        stroller_ok=True,
        start_point="Südpark Eingang",
        route_steps=["Zur Wiese laufen", "Auf Decke legen"],
        preparation=["Wetter prüfen"],
        packing_list=["Decke", "Wasser"],
        execution_tips=["Kind bestimmen lassen"],
        variations=["Wolken malen"],
        toddler_benefits=["Sprache", "Achtsamkeit"],
        carla_tip="Nicht überplanen",
        risks=["Sonne"],
        mitigations=["Sonnenhut"],
        tags=["Natur"],
    )


def test_render_daily_email_html_renders_core_content() -> None:
    adventure = _sample_adventure()
    criteria = ActivitySearchCriteria(
        time_window=TimeWindow(start=time(9, 0), end=time(10, 0))
    )
    day = date(2026, 1, 1)
    markdown_body = "# Tagesplan\n- Marker: Picknick"

    html = render_daily_email_html(
        adventure, criteria, day, markdown_body, weather=None
    )

    assert adventure.title in html
    assert day.isoformat() in html
    assert "Notfall: 112" in html
    assert "Marker: Picknick" in html
