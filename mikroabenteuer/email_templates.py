from __future__ import annotations

from mikroabenteuer.models import Adventure


def build_html_mail(adventure: Adventure) -> str:
    """Build bilingual HTML email with inline styles."""
    risks = "".join(f"<li>{risk}</li>" for risk in adventure.safety.risks)
    return f"""
<html>
<body style="font-family:Arial,sans-serif; background:#f4f8f4; margin:0; padding:20px; color:#1f2937;">
  <div style="max-width:640px; margin:auto; background:#ffffff; padding:24px; border-radius:12px; border:1px solid #dce6dc;">
    <p style="margin:0 0 8px; color:#2e7d32; font-size:14px;">Daily adventure / Tagesabenteuer</p>
    <h1 style="margin:0 0 12px; color:#2e7d32;">🌿 {adventure.title}</h1>
    <p style="margin:6px 0;"><b>Ort / Location:</b> {adventure.location}</p>
    <p style="margin:6px 0;"><b>Dauer / Duration:</b> {adventure.duration}</p>

    <h3 style="margin:18px 0 8px;">✨ Motto</h3>
    <p style="margin:0 0 12px;">{adventure.intro_quote}</p>

    <h3 style="margin:18px 0 8px;">🧠 Warum gut für Carla? / Why it's good for Carla?</h3>
    <p style="margin:0 0 12px;">{adventure.child_benefit}</p>

    <h3 style="margin:18px 0 8px;">⚠ Sicherheit / Safety</h3>
    <ul style="margin:0; padding-left:20px;">{risks}</ul>
  </div>
</body>
</html>
""".strip()
