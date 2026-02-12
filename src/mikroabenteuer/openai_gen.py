# src/mikroabenteuer/openai_gen.py
from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from .config import AppConfig
from .models import ActivitySearchCriteria, MicroAdventure
from .weather import WeatherSummary


def _fallback_daily_markdown(adventure: MicroAdventure, criteria: ActivitySearchCriteria, weather: Optional[WeatherSummary]) -> str:
    weather_line = "Wetter: (nicht geladen)"
    if weather:
        parts = []
        if weather.temperature_max_c is not None:
            parts.append(f"max {weather.temperature_max_c:.0f}°C")
        if weather.precipitation_probability_max is not None:
            parts.append(f"Regenwahrscheinlichkeit {weather.precipitation_probability_max:.0f}%")
        if weather.windspeed_max_kmh is not None:
            parts.append(f"Wind {weather.windspeed_max_kmh:.0f} km/h")
        weather_line = "Wetter: " + (", ".join(parts) if parts else ", ".join(weather.derived_tags))

    return f"""# Mikroabenteuer des Tages 🌿

**{adventure.title}**  
*Ort:* {adventure.area} · *Dauer:* {adventure.duration_minutes} min · *Distanz:* {adventure.distance_km} km  
{weather_line}

## Motivations‑One‑Liner
„Heute machen wir was Kleines – aber mit großem Kinder‑Staunen.“

## Plan (kurz & klar)
**Startpunkt:** {adventure.start_point}

**Route / Ablauf:**
{chr(10).join([f"- {s}" for s in adventure.route_steps])}

## Vorbereitung
{chr(10).join([f"- {s}" for s in adventure.preparation])}

## Packliste
{chr(10).join([f"- {s}" for s in adventure.packing_list])}

## Durchführungstipps
{chr(10).join([f"- {s}" for s in adventure.execution_tips])}

## Vorteil für Carla (2,5)
{chr(10).join([f"- {s}" for s in adventure.toddler_benefits])}

**Carla‑Tipp:** {adventure.carla_tip}

## Sicherheit
**Risiken:** {", ".join(adventure.risks) if adventure.risks else "—"}  
**Gegenmaßnahmen:** {", ".join(adventure.mitigations) if adventure.mitigations else "—"}
"""


def generate_daily_markdown(
    cfg: AppConfig,
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
    weather: Optional[WeatherSummary],
) -> str:
    """
    Uses OpenAI Responses API if enabled, else fallback template.

    Web search is enabled via cfg.enable_web_search (tool: web_search).
    """
    if not cfg.enable_llm or not cfg.openai_api_key:
        return _fallback_daily_markdown(adventure, criteria, weather)

    # Import lazily so the app still runs without openai installed/available.
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return _fallback_daily_markdown(adventure, criteria, weather)

    client = OpenAI(api_key=cfg.openai_api_key)

    weather_payload = None
    if weather:
        weather_payload = {
            "day": weather.day.isoformat(),
            "temperature_max_c": weather.temperature_max_c,
            "temperature_min_c": weather.temperature_min_c,
            "precipitation_probability_max": weather.precipitation_probability_max,
            "precipitation_sum_mm": weather.precipitation_sum_mm,
            "windspeed_max_kmh": weather.windspeed_max_kmh,
            "derived_tags": weather.derived_tags,
        }

    prompt = f"""
Du planst ein Mikroabenteuer für ein Kleinkind (2,5 Jahre) in Düsseldorf (Fokus: Volksgarten/Südpark).

Gib aus:
1) Einen motivierenden, lustigen One‑Liner ganz am Anfang (1 Zeile).
2) Einen konkreten Plan mit Startpunkt, Ablauf (Steps), Dauer, Distanz – praktisch, kleinkindgerecht.
3) Vorbereitung + Packliste + Durchführungstipps (knapp aber hilfreich).
4) Täglichen Tipp: Warum die Idee gut ist & Nutzen für Carla.
5) Sicherheit: Gefahren + Reiseapotheke/Notfall‑Hinweise (realistisch, nicht panisch).
6) Wenn Websuche aktiv ist: 1–2 lokale Mikro‑Tipps (z. B. ruhige Stelle/geeigneter Weg), aber ohne falsche Details zu erfinden.

Schreibe auf Deutsch. Verwende klare Markdown‑Überschriften.

Kriterien:
{criteria.model_dump_json(indent=2)}

Wetter (optional):
{weather_payload}

Abenteuer‑Seed:
{adventure.__dict__}
""".strip()

    tools = [{"type": "web_search"}] if cfg.enable_web_search else []

    try:
        resp = client.responses.create(
            model=cfg.openai_model,
            input=[
                {"role": "developer", "content": "Du bist ein zuverlässiger, vorsichtiger Outdoor‑Planer für Kleinkinder. Keine erfundenen Fakten."},
                {"role": "user", "content": prompt},
            ],
            tools=tools,
        )
        text = getattr(resp, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        # last resort: stringify
        return str(resp)
    except Exception:
        return _fallback_daily_markdown(adventure, criteria, weather)
