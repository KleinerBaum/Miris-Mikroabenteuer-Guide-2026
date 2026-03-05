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
- **Sichere Feldtyp-Hinweise bei Schema-Fehlern / Safe field-type hints for schema failures:** Bei Structured-Output-Validierungsfehlern werden ausschließlich sichere Metadaten (Feldpfad + Fehlertyp) in DE/EN angezeigt, damit klar ist, ob ein Retry sinnvoll ist – ohne Rohdaten/PII auszugeben.  
  → `src/mikroabenteuer/openai_activity_service.py`, `app.py`
- **Schema-Reparatur + Best-Effort-Wiederherstellung / Schema repair + best-effort recovery:** Bei Parse-Fehlern erfolgt ein zweiter Responses-Call mit explizitem JSON-Reparaturhinweis; falls weiterhin ungültig, wird ein minimaler Titel/Quelle/Beschreibung-Pfad extrahiert und streng normalisiert, bevor erst danach der Offline-Fallback greift.  
  → `src/mikroabenteuer/openai_activity_service.py`
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
- **Dynamische Familienüberschrift / Dynamic family headline**: Sidebar-Namensfelder starten ohne Default-Werte; die Titelzeile baut sich aus den aktuellen Eingaben auf, mit robusten Fallbacks „Kind“/„Eltern“.  
  → `app.py`
- **Button- und Select-Kontraste verfeinert / Refined button and select contrast**: bessere Lesbarkeit für primäre Buttons im Hover-Zustand sowie konsistente, helle Select-/MultiSelect-Hintergründe inkl. Icons.
- **Dunkle Button-Flächen aufgehellt / Dark button surfaces lightened**: Sekundäre Buttons in Inputs und Select-Komponenten nutzen jetzt appweit helle Hintergründe (inkl. Hover), um Lesbarkeit von Text und Icons sicherzustellen.  
  → `app.py`
- **UI-Flow neu strukturiert:** Wetter & Veranstaltungen werden über die Sidebar gesteuert; Ergebnisse erscheinen direkt unter dem Tagesabenteuer im Hauptbereich.  
  → `app.py`
- **Daily-Export in der Sidebar / Daily export in the sidebar:** Die komplette Sektion „Export“ (JSON/Markdown/ICS), „E-Mail-Vorschau“ und „Automatisierung (optional)“ liegt jetzt ausschließlich in der Sidebar und wurde aus der Landing-Page entfernt.  
  → `app.py`
- **Deklarative Filter-UI / Declarative filter UI:** Gemeinsame Kernfilter für Sidebar und Wetter/Events werden über ein zentrales Feldschema (`FilterFieldSpec`) gerendert; nur mode-spezifische Felder bleiben separat.  
  → `src/mikroabenteuer/ui/filter_specs.py`, `app.py`
- **Zentraler UI-State-Keyspace / Central UI state keyspace:** Widget-Keys für tägliche Suche und Wetter/Events werden über einen typisierten Resolver (`CriteriaKeySpace`) erzeugt; fachlicher Criteria-State bleibt in `CRITERIA_DAILY_KEY`/`CRITERIA_EVENTS_KEY`.  
  → `src/mikroabenteuer/ui/state_keys.py`, `app.py`
- **Filter-Vertrags-Regressionstests / Filter contract regression tests:** Tests sichern den gemeinsamen Kernfeldkatalog (Daily/Events), Keyspace-Namespaces und das Mapping der Location-Präferenzen (`outdoor`/`indoor`/`mixed`) gegen stilles Drift-Verhalten ab.  
  → `tests/test_criteria_state_isolation.py`
- **Normalisierte Filter-Inputs / Normalized filter inputs:** Widget-Eingaben werden vor dem Criteria-Building in ein gemeinsames Zwischenmodell normalisiert; Events-Sonderfälle (Toggle-Location, optionale Constraints, Kontext-Trunkierung) sind in wiederverwendbaren Normalizern gekapselt und Validierungsfehler werden konsistent gerendert.  
  → `app.py`
- **Bibliothek als eigene Seite:** Die Abenteuerliste wurde in eine separate Streamlit-Seite ausgelagert und als kompakte Kartenansicht umgesetzt.  
  → `pages/2_Bibliothek.py`
- **Bibliothek: In-Page Filterleiste in 3 Spalten / Library: in-page filter bar in 3 columns:** Auf der Bibliothek-Seite stehen Suche und Filter jetzt direkt unter der Überschrift in drei gruppierten Spalten; standardmäßig sind keine Filter gesetzt und die komplette Abenteuerliste ist sichtbar.  
  → `pages/2_Bibliothek.py`
- **Prominente Seiten-Navigation & kompakte Filter / Prominent page navigation & compact filters:** In der Sidebar stehen „Mikroabenteuer des Tages“ und „Bibliothek“ jetzt oben als direkte Navigation. Daily- und Bibliothek-Filter zeigen primär nur essentielle Felder; weitere Optionen sind in bis zu drei aufklappbaren Gruppen gebündelt. Auf Mobile ist der Sidebar-Hintergrund vollständig undurchsichtig.  
  → `app.py`, `pages/2_Bibliothek.py`, `src/mikroabenteuer/ui/sidebar_nav.py`
- **Landingpage: 2 Hauptsektionen / Landing page: 2 main sections:** Die Landingpage ist in „Abenteuer des Tages“ und „Suche von Aktivitäten“ gegliedert. In der Suchsektion ist „Suche (Schnellzugriff)“ standardmäßig ausgeklappt und als 3‑Spalten‑Layout umgesetzt; „Plan melden“ bleibt enthalten und „Gemeldete Pläne ansehen“ wurde entfernt.  
  → `app.py`

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


### 2) Optionale `.env`-Konfiguration (Events/LLM)

```env
ENABLE_LLM=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL_EVENTS_FAST=gpt-4o-mini
OPENAI_MODEL_EVENTS_ACCURATE=o3-mini
MAX_INPUT_CHARS=4000
MAX_OUTPUT_TOKENS=1400
TIMEOUT_S=45
```

Hinweis: Für stabile Event-Structured-Outputs ist `MAX_OUTPUT_TOKENS=1400` der neue robuste Standard (überschreibbar per Env).
