
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
- **Event-Output stabilisiert / Event output stabilized:** Standard für `MAX_OUTPUT_TOKENS` wurde auf 1400 erhöht; Event-Prompts erzwingen kompakte Vorschläge (kurze Beschreibung, max. 2 Quellen, keine Wetter-/Kriterien-Wiederholung) und deckeln bei sehr langem Kontext die gewünschte Anzahl Vorschläge dynamisch auf maximal 4, um Structured-Output-Degeneration zu vermeiden.
- **Responses-Schema-Reparaturkette / Responses schema-repair chain:** Eventsuche versucht nach Parse-/Schema-Fehlern zuerst einen zweiten kontrollierten Responses-Call mit explizitem JSON-Reparaturhinweis, danach eine minimale Best-Effort-Extraktion (Titel/Quelle/Beschreibung) mit strikter Normalisierung; nur dann folgt der bestehende Offline-Fallback. Ein klarer Recovery-Marker wird in `warnings_de_en` gesetzt, wenn die Wiederherstellung gelingt.
- **Bibliothek-Filter auf der Seite selbst / On-page library filters:** Such- und Filterfunktionen sind nun direkt auf der Seite „Bibliothek“ unterhalb der Überschrift in drei Spalten angeordnet; ohne gesetzte Filter wird standardmäßig die vollständige Abenteuerliste angezeigt.
- **Daily-Export vollständig in Sidebar / Daily export fully moved to sidebar:** Die Sektion „Export“ inklusive JSON/Markdown/ICS sowie „E-Mail-Vorschau“ und „Automatisierung (optional)“ wurde aus der Landing-Page entfernt und komplett in die Sidebar verlegt.
- **UI-Key-Resolver zentralisiert / Centralized UI key resolver:** Neue `CriteriaKeySpace`-Abstraktion (`daily`/`events` → `sidebar`/`form`) erzeugt Widget-Keys zentral; die Criteria-Domain-States (`CRITERIA_DAILY_KEY`/`CRITERIA_EVENTS_KEY`) bleiben davon entkoppelt und weiterhin fachliche Single Source of Truth.
- **Deklarative Filter-Spezifikation eingeführt / Declarative filter specification introduced:** Gemeinsame Filterfelder werden jetzt zentral als `FilterFieldSpec` in `src/mikroabenteuer/ui/filter_specs.py` gepflegt und über eine einheitliche Render-Funktion in Sidebar und Wetter/Events-Form wiederverwendet; mode-spezifische Zusätze (z. B. Genauigkeit, Event-Kontext) bleiben separat.
- **Fehlerklassen für Eventsuche differenziert / Event-search error classes differentiated:** `suggest_activities` unterscheidet jetzt fehlenden API-Key, retrybare Upstream-Fehler (Rate-Limit/5xx/Timeout), Structured-Output-Validierungsfehler und sonstige nicht-retrybare API-Fehler; zusätzlich werden `error_code` und `error_hint_de_en` im Ergebnis geführt und in Orchestrierung/UI gezielt angezeigt.
- **Sichere Validierungsdetails in Event-Fehlerhinweisen / Safe validation metadata in event error hints:** Bei `ValidationError` werden nur Feldpfad + Fehlertyp (ohne Nutzdaten/PII) extrahiert und als technische Notiz ausgegeben; die UI zeigt zusätzlich eine kurze DE/EN-Zeile mit dem fehlgeschlagenen Feldtyp (z. B. `suggestions[0].source_urls[0] url_parsing`) für eine bessere Retry-Entscheidung.
- **Button- und Select-Kontraste nachgeschärft / Improved button and select contrast:** Primäre Buttons behalten im Hover-Zustand nun einen dunklen, gut lesbaren Hintergrund; Select-/MultiSelect-Flächen und Icons wurden für bessere Lesbarkeit auf hellem Theme-Hintergrund vereinheitlicht.
- **Event-Geo-Kontext aus Suchkriterien / Event geo context from search criteria:** Für den Event-Wetter-Pfad wird Standortkontext jetzt PLZ-basiert aufgelöst (city/region/country/timezone), und `web_search.user_location` wird nur bei validen Daten gesetzt; hartcodierte Stadtwerte wurden entfernt.
- **Filter-Normalisierung vereinheitlicht / Unified filter normalization:** Gemeinsame Normalisierung von Widget-Werten (`normalize_widget_input`) erzeugt ein konsistentes Zwischenmodell; Event-Sonderfälle (Location-Toggles, optionale Constraints, Kontext-Trunkierung) wurden in klar benannte Normalizer ausgelagert, und ValidationErrors werden in Daily-/Events-Pfad identisch dargestellt.
- **Packaging für Cloud-Deployments / Packaging for cloud deployments:** `requirements.txt` installiert jetzt das lokale `src`-Package via `-e .`, damit `import mikroabenteuer` auch in Streamlit-Cloud-ähnlichen Umgebungen funktioniert; Docker-Installationsreihenfolge ist damit kompatibel.
- Standard-`src`-Layout umgesetzt: Package unter `src/mikroabenteuer` wird als `mikroabenteuer.*` importiert; `src/__init__.py` entfernt; Packaging via `pyproject.toml` + Editable Install (`pip install -e .`) ergänzt.
- **UI-Kontrast verbessert / Improved UI contrast:** Formularfelder, Selects, Slider und Tags nutzen jetzt hellere Flächen und klarere Schriftfarben für bessere Lesbarkeit bei der bisherigen dunklen Komponenten-Optik.
- **Migration konsolidiert / Migration consolidated:** V2-Importpfade bleiben kanonisch (`mikroabenteuer.*`), V1 bleibt Legacy, und nicht mehr genutzte Dependencies wurden aus den Runtime-Anforderungen entfernt.
- **Import-Guardrails hinzugefügt / Import guardrails added:** Neue Tests verhindern in aktivem Code Rückfälle auf `src.mikroabenteuer`- oder `legacy.v1`-Imports.

### Changed / Geändert
- **Responses-Schema-Reparaturkette / Responses schema-repair chain:** Eventsuche versucht nach Parse-/Schema-Fehlern zuerst einen zweiten kontrollierten Responses-Call mit explizitem JSON-Reparaturhinweis, danach eine minimale Best-Effort-Extraktion (Titel/Quelle/Beschreibung) mit strikter Normalisierung; nur dann folgt der bestehende Offline-Fallback. Ein klarer Recovery-Marker wird in `warnings_de_en` gesetzt, wenn die Wiederherstellung gelingt.
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
- **Responses-Schema-Reparaturkette / Responses schema-repair chain:** Eventsuche versucht nach Parse-/Schema-Fehlern zuerst einen zweiten kontrollierten Responses-Call mit explizitem JSON-Reparaturhinweis, danach eine minimale Best-Effort-Extraktion (Titel/Quelle/Beschreibung) mit strikter Normalisierung; nur dann folgt der bestehende Offline-Fallback. Ein klarer Recovery-Marker wird in `warnings_de_en` gesetzt, wenn die Wiederherstellung gelingt.
- CI via GitHub Actions (`.github/workflows/ci.yml`) mit ruff + pytest + import‑smoke.
- Pre-commit hooks inkl. detect-secrets baseline (`.pre-commit-config.yaml`, `.secrets.baseline`).

### Security / Sicherheit
- Moderation vor/nach OpenAI Calls + PII‑Maskierung, um keine Roh‑PII an LLM Endpoints zu senden.
- Regelbasierte Safety-Validierung für generierte Plans mit sicheren Fallbacks.
