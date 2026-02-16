
---

```md
# CHANGELOG.md

# Changelog

All notable changes to this project will be documented in this file.

Format inspired by “Keep a Changelog”.  
Language: We keep entries short and typically bilingual (DE/EN) when user-facing behavior changes.

---

## Unreleased

### Changed / Geändert
- Standard-`src`-Layout umgesetzt: Package unter `src/mikroabenteuer` wird als `mikroabenteuer.*` importiert; `src/__init__.py` entfernt; Packaging via `pyproject.toml` + Editable Install (`pip install -e .`) ergänzt.
- **UI-Kontrast verbessert / Improved UI contrast:** Formularfelder, Selects, Slider und Tags nutzen jetzt hellere Flächen und klarere Schriftfarben für bessere Lesbarkeit bei der bisherigen dunklen Komponenten-Optik.

### Planned / Geplant
- **Streamlit State Hardening:** Kriterien-State sauber trennen (Sidebar vs. Wetter/Events‑Form), Event/Plan Ergebnisse per Fingerprint in `st.session_state` cachen.
- **Config Cleanup:** Environment variable naming vereinheitlichen (Google OAuth / Settings vs. Config), Hardcoded Modell-Auswahl in Events in Config überführen.

### Known Issues / Bekannte Punkte
- Doppelter Codepfad (V1/V2) erhöht Wartungsaufwand und sorgt für Import‑Konfusion.
- In der aktuellen UI können Reruns zu unnötigen Neuberechnungen führen (geplant: Fingerprint‑Caching).

---

## 0.1.0 — 2026-02-14

### Added / Hinzugefügt
- Streamlit App `app.py` für Mikroabenteuer-Auswahl, Tagesansicht und Exporte.
- V2 Package `src/mikroabenteuer/*` mit:
  - kanonischen Pydantic Modellen (`ActivitySearchCriteria`, `ActivityPlan`, …)
  - Seed-Bibliothek (`data_seed.py`) + Recommender (`recommender.py`)
  - Wetter via Open‑Meteo (ohne API-Key) (`weather.py`)
  - Offline-Activity-Library (`data/activity_library.json`) + Offline‑Scoring (`activity_library.py`)
  - OpenAI Responses API Structured Output + Safety Guardrails (`openai_gen.py`)
  - Event-/Activity Web‑Recherche via `web_search` Tool (`openai_activity_service.py`, `activity_orchestrator.py`)
  - PII‑Redaction + Moderation (`pii_redaction.py`, `moderation.py`)
  - Plan reports (hash+reason, no PII) (`plan_reports.py`)
  - Exporte: Markdown/JSON/ICS + HTML Email Template (`ics.py`, `email_templates.py`)
  - Google OAuth Integrationen (Gmail/Calendar) (`google_auth.py`, `gmail_api.py`, `gcal_api.py`)
  - Daily job runner (`scheduler.py`)

### Changed / Geändert
- CI via GitHub Actions (`.github/workflows/ci.yml`) mit ruff + pytest + import‑smoke.
- Pre-commit hooks inkl. detect-secrets baseline (`.pre-commit-config.yaml`, `.secrets.baseline`).

### Security / Sicherheit
- Moderation vor/nach OpenAI Calls + PII‑Maskierung, um keine Roh‑PII an LLM Endpoints zu senden.
- Regelbasierte Safety-Validierung für generierte Plans mit sicheren Fallbacks.
