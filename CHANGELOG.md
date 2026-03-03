
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
- **Deklarative Filter-Spezifikation eingeführt / Declarative filter specification introduced:** Gemeinsame Filterfelder werden jetzt zentral als `FilterFieldSpec` in `src/mikroabenteuer/ui/filter_specs.py` gepflegt und über eine einheitliche Render-Funktion in Sidebar und Wetter/Events-Form wiederverwendet; mode-spezifische Zusätze (z. B. Genauigkeit, Event-Kontext) bleiben separat.
- **Fehlerklassen für Eventsuche differenziert / Event-search error classes differentiated:** `suggest_activities` unterscheidet jetzt fehlenden API-Key, retrybare Upstream-Fehler (Rate-Limit/5xx/Timeout), Structured-Output-Validierungsfehler und sonstige nicht-retrybare API-Fehler; zusätzlich werden `error_code` und `error_hint_de_en` im Ergebnis geführt und in Orchestrierung/UI gezielt angezeigt.
- **Button- und Select-Kontraste nachgeschärft / Improved button and select contrast:** Primäre Buttons behalten im Hover-Zustand nun einen dunklen, gut lesbaren Hintergrund; Select-/MultiSelect-Flächen und Icons wurden für bessere Lesbarkeit auf hellem Theme-Hintergrund vereinheitlicht.
- **Event-Geo-Kontext aus Suchkriterien / Event geo context from search criteria:** Für den Event-Wetter-Pfad wird Standortkontext jetzt PLZ-basiert aufgelöst (city/region/country/timezone), und `web_search.user_location` wird nur bei validen Daten gesetzt; hartcodierte Stadtwerte wurden entfernt.
- **Packaging für Cloud-Deployments / Packaging for cloud deployments:** `requirements.txt` installiert jetzt das lokale `src`-Package via `-e .`, damit `import mikroabenteuer` auch in Streamlit-Cloud-ähnlichen Umgebungen funktioniert; Docker-Installationsreihenfolge ist damit kompatibel.
- Standard-`src`-Layout umgesetzt: Package unter `src/mikroabenteuer` wird als `mikroabenteuer.*` importiert; `src/__init__.py` entfernt; Packaging via `pyproject.toml` + Editable Install (`pip install -e .`) ergänzt.
- **UI-Kontrast verbessert / Improved UI contrast:** Formularfelder, Selects, Slider und Tags nutzen jetzt hellere Flächen und klarere Schriftfarben für bessere Lesbarkeit bei der bisherigen dunklen Komponenten-Optik.
- **Migration konsolidiert / Migration consolidated:** V2-Importpfade bleiben kanonisch (`mikroabenteuer.*`), V1 bleibt Legacy, und nicht mehr genutzte Dependencies wurden aus den Runtime-Anforderungen entfernt.
- **Import-Guardrails hinzugefügt / Import guardrails added:** Neue Tests verhindern in aktivem Code Rückfälle auf `src.mikroabenteuer`- oder `legacy.v1`-Imports.

### Changed / Geändert
- **Deutschsprachige UI vereinheitlicht:** Sichtbare UI-Texte im Tagesplan, in Fallback-Plänen und im Wetter/Events-Flow sind jetzt rein deutsch; englische Slash-Texte wurden entfernt.
- **Tagesabenteuer-Layout verbessert:** Aktivitätstitel wird im Hauptbereich als eigene Überschrift gerendert; Planabschnitte werden strukturiert angezeigt, wobei "Sicherheit" eingeklappt startet.
- **Wetter & Veranstaltungen in die Sidebar verschoben:** Eingabeformular, Aktionen und Event-Exporte liegen jetzt in der Sidebar; Ergebnisse werden im Hauptbereich unter dem Tagesabenteuer gerendert.
- **Bibliothek als eigene Seite:** Hauptseite zeigt nur Suche, Tagesabenteuer und Events; die Abenteuerbibliothek ist nun als Streamlit-Seite unter `pages/2_Bibliothek.py` umgesetzt und mit kompakten Karten statt Tabelle dargestellt.

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
