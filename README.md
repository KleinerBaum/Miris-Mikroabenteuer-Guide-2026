# README.md

# 🌿 Miris Mikroabenteuer Guide 2026

[![CI](https://github.com/KleinerBaum/Miris-Mikroabenteuer-Guide-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/KleinerBaum/Miris-Mikroabenteuer-Guide-2026/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Eine **Streamlit-Webapp**, die täglich (und filterbar) **Mikroabenteuer** vorschlägt und daraus auf Wunsch einen **sicheren, strukturierten Activity-Plan** erzeugt – gedacht für **Miri (Mama) & Carla (Kind)**, standardmäßig rund um **Düsseldorf (Volksgarten/Südpark)**.

Die App kann:
- **ohne LLM** (offline/curated) laufen,
- optional mit **OpenAI Responses API** + **Structured Output** + **Moderation** + **PII-Redaction** arbeiten,
- Markdown/JSON/ICS exportieren,
- optional per OAuth **Gmail** senden / **Google Calendar** Events anlegen.

---

## Highlights

- **Seed-Bibliothek** (kuratierte Mikroabenteuer) + Filter & Ranking  
  → `src/mikroabenteuer/data_seed.py`, `src/mikroabenteuer/recommender.py`
- **Wetter** (Open‑Meteo, ohne API-Key)  
  → `src/mikroabenteuer/weather.py`
- **“Wetter & Events”**: Web‑Recherche über OpenAI `web_search` Tool (optional) + Offline‑Fallback  
  → `src/mikroabenteuer/openai_activity_service.py`, `src/mikroabenteuer/activity_orchestrator.py`
- **Fehlerhinweise pro Klasse / Class-specific error hints:** Bei Event-Fehlern zeigt die UI jetzt differenzierte DE/EN-Hinweise für API-Key, retrybare Upstream-Probleme, Structured-Output-Validierung und nicht-retrybare API-Fehler.  
  → `src/mikroabenteuer/openai_activity_service.py`, `app.py`
- **PLZ-basierte Standortauflösung für Event-Suche / Postal-code based location resolution for event search**: `user_location` wird nur mit validen Ortsdaten an das `web_search`-Tool übergeben; keine hartcodierte Stadt im Event-Wetter-Pfad.  
  → `app.py`, `src/mikroabenteuer/openai_activity_service.py`
- **LLM-Planung als Schema** (`ActivityPlan`) + Safety‑Validator + “Plan B” Varianten  
  → `src/mikroabenteuer/openai_gen.py`, `src/mikroabenteuer/models.py`
- **Privacy & Safety**: PII‑Redaction vor Requests, Moderation vor/nach LLM  
  → `src/mikroabenteuer/pii_redaction.py`, `src/mikroabenteuer/moderation.py`
- **Plan melden** (ohne PII): speichert nur Hash + Grund + UTC‑Zeit  
  → `src/mikroabenteuer/plan_reports.py` (default: `data/plan_reports.jsonl`)
- **CI & Pre‑commit**: ruff + pytest + detect-secrets  
  → `.github/workflows/ci.yml`, `.pre-commit-config.yaml`
- **Verbesserte Lesbarkeit in der UI / Improved UI readability**: überarbeitetes Farbschema für Form-Controls (Inputs, Selects, Slider, Tags) mit höherem Kontrast.  
  → `app.py`
- **Button- und Select-Kontraste verfeinert / Refined button and select contrast**: bessere Lesbarkeit für primäre Buttons im Hover-Zustand sowie konsistente, helle Select-/MultiSelect-Hintergründe inkl. Icons.  
  → `app.py`
- **UI-Flow neu strukturiert:** Wetter & Veranstaltungen werden über die Sidebar gesteuert; Ergebnisse erscheinen direkt unter dem Tagesabenteuer im Hauptbereich.  
  → `app.py`
- **Deklarative Filter-UI / Declarative filter UI:** Gemeinsame Kernfilter für Sidebar und Wetter/Events werden über ein zentrales Feldschema (`FilterFieldSpec`) gerendert; nur mode-spezifische Felder bleiben separat.  
  → `src/mikroabenteuer/ui/filter_specs.py`, `app.py`
- **Zentraler UI-State-Keyspace / Central UI state keyspace:** Widget-Keys für tägliche Suche und Wetter/Events werden über einen typisierten Resolver (`CriteriaKeySpace`) erzeugt; fachlicher Criteria-State bleibt in `CRITERIA_DAILY_KEY`/`CRITERIA_EVENTS_KEY`.  
  → `src/mikroabenteuer/ui/state_keys.py`, `app.py`
- **Normalisierte Filter-Inputs / Normalized filter inputs:** Widget-Eingaben werden vor dem Criteria-Building in ein gemeinsames Zwischenmodell normalisiert; Events-Sonderfälle (Toggle-Location, optionale Constraints, Kontext-Trunkierung) sind in wiederverwendbaren Normalizern gekapselt und Validierungsfehler werden konsistent gerendert.  
  → `app.py`
- **Bibliothek als eigene Seite:** Die Abenteuerliste wurde in eine separate Streamlit-Seite ausgelagert und als kompakte Kartenansicht umgesetzt.  
  → `pages/2_Bibliothek.py`

---

## Architekturstatus (wichtig)

Aktuell gibt es **zwei Codebasen**:

- **V2 (aktiv):** `src/mikroabenteuer/*` (importierbar als `mikroabenteuer.*`)  
  Wird von `app.py` genutzt und enthält die aktuellen Pydantic‑Schemas, LLM‑Structured Outputs etc.
- **V1 (legacy):** `legacy/v1/*`  
  Ältere Implementationen (YAML Seed, legacy Engine, legacy ICS/Google).

👉 **Neue Entwicklung bitte in V2 (`src/mikroabenteuer`) machen.**

---

## Quickstart (lokal)

### 1) Setup

```bash
git clone https://github.com/KleinerBaum/Miris-Mikroabenteuer-Guide-2026.git
cd Miris-Mikroabenteuer-Guide-2026

python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
