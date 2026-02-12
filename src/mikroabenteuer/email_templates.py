# src/mikroabenteuer/email_templates.py
from __future__ import annotations

import html
from datetime import date
from typing import Optional

from .models import ActivitySearchCriteria, MicroAdventure
from .weather import WeatherSummary


def _simple_markdown_to_html(md: str) -> str:
    """
    Minimal markdown -> HTML converter (no external deps).
    Supports:
    - #/##/### headings
    - bullet lists starting with "- "
    - paragraph breaks
    """
    lines = md.splitlines()
    html_lines = []
    in_ul = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            close_ul()
            html_lines.append("<div style='height:10px'></div>")
            continue

        esc = html.escape(line)

        if esc.startswith("### "):
            close_ul()
            html_lines.append(f"<h3 style='margin:14px 0 6px 0; font-size:16px;'>{esc[4:]}</h3>")
        elif esc.startswith("## "):
            close_ul()
            html_lines.append(f"<h2 style='margin:16px 0 8px 0; font-size:18px;'>{esc[3:]}</h2>")
        elif esc.startswith("# "):
            close_ul()
            html_lines.append(f"<h1 style='margin:0 0 10px 0; font-size:20px;'>{esc[2:]}</h1>")
        elif esc.startswith("- "):
            if not in_ul:
                html_lines.append("<ul style='margin:6px 0 10px 18px; padding:0;'>")
                in_ul = True
            html_lines.append(f"<li style='margin:4px 0;'>{esc[2:]}</li>")
        else:
            close_ul()
            html_lines.append(f"<p style='margin:6px 0; line-height:1.4;'>{esc}</p>")

    close_ul()
    return "\n".join(html_lines)


def render_daily_email_html(
    adventure: MicroAdventure,
    criteria: ActivitySearchCriteria,
    day: date,
    markdown_body: str,
    weather: Optional[WeatherSummary] = None,
) -> str:
    subtitle_parts = [adventure.area, f"{adventure.duration_minutes} min", f"{adventure.distance_km:.1f} km"]
    if weather:
        subtitle_parts.append(" · ".join(weather.derived_tags))

    subtitle = " · ".join(subtitle_parts)

    body_html = _simple_markdown_to_html(markdown_body)

    # Inline-styled HTML for Gmail
    return f"""\
<!doctype html>
<html>
  <body style="margin:0; padding:0; background:#f6f7fb; font-family: Arial, Helvetica, sans-serif;">
    <div style="max-width:680px; margin:0 auto; padding:18px;">
      <div style="background:#ffffff; border-radius:14px; padding:18px; border:1px solid #e7e9f3;">
        <div style="font-size:12px; color:#667085; letter-spacing:0.3px;">
          Mikroabenteuer mit Carla · {day.isoformat()}
        </div>

        <div style="margin-top:6px; font-size:22px; font-weight:700; color:#101828;">
          {adventure.title}
        </div>

        <div style="margin-top:6px; font-size:13px; color:#475467;">
          {subtitle}
        </div>

        <div style="margin-top:16px; border-top:1px solid #eef0f7;"></div>

        <div style="margin-top:14px; color:#101828;">
          {body_html}
        </div>

        <div style="margin-top:16px; border-top:1px solid #eef0f7;"></div>

        <div style="margin-top:12px; font-size:12px; color:#667085; line-height:1.4;">
          Tipp: Plane lieber zu kurz als zu lang. Abbrechen ist ein Feature. 😊<br/>
          Notfall: 112
        </div>
      </div>

      <div style="margin-top:10px; font-size:11px; color:#98A2B3; text-align:center;">
        Dieses Abenteuer ist ein Geschenk – kein Leistungsprogramm.
      </div>
    </div>
  </body>
</html>
"""
