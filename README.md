# 🌿 Mikroabenteuer mit Carla

[![CI](https://github.com/<OWNER>/Miris-Mikroabenteuer-Guide-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/<OWNER>/Miris-Mikroabenteuer-Guide-2026/actions/workflows/ci.yml)

_Hinweis: `<OWNER>` im Badge-Link durch den GitHub-Owner des Repositories ersetzen._

Eine Streamlit-Webapp für tägliche Mikroabenteuer rund um Düsseldorf (Fokus: Volksgarten / Südpark).
Die App basiert auf einer Seed-Bibliothek von Aktivitäten mit Detailansichten und V2-Klassifikation
(Saison/Wetter/Energie/Schwierigkeit/Safety/Mood/Alter), damit Filter und spätere LLM-Aufrufe konsistente Parameter haben.

---

## Features (aktuell / geplant)

**Aktuell:**
- Seed-Bibliothek (`src/mikroabenteuer/data_seed.py`)
- Täglicher Vorschlag (deterministisch pro Datum, wenn implementiert in `recommender.py`)
- Übersicht + Detailansichten (Accordion/Expander)
- Safety-Hinweise pro Aktivität (Basis)

**Vorbereitet (V2 Meta vorhanden, UI kann darauf filtern):**
- Filter nach Saison, Wetter, Energie, Safety, Alter, Mood

**Geplant (Roadmap):**
- Wetterbasierte Auswahl / lokale Tipps
- Daily Email Versand + ICS (später)

---

## CI (GitHub Actions)

- Workflow: `.github/workflows/ci.yml`
- Trigger: bei jedem Pull Request (`pull_request`)
- Checks: `ruff format --check`, `ruff check`, `pytest -m "not integration"`, `python -c "import app"`
- Optional local guardrails (pre-commit): `ruff-format`, `ruff`, `black`, and `detect-secrets` via `.pre-commit-config.yaml` to prevent accidental secret commits.
- Optional lokale Guardrails (pre-commit): `ruff-format`, `ruff`, `black` und `detect-secrets` über `.pre-commit-config.yaml`, um versehentliche Secret-Commits zu verhindern.

## Quickstart (lokal)

### 1) Repo + venv

```bash
git clone <repo-url>
cd mikroabenteuer-mit-carla

python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 2) Abhängigkeiten installieren

```bash
pip install -r requirements.txt
python -c "import openai; print(openai.__version__)"
```

`requirements.txt` enthält `openai>=1.0`, damit die Wetter-&-Events-Recherche zuverlässig das OpenAI-SDK laden kann.

### 3) App starten

```bash
streamlit run app.py
```

---

## Konfiguration
- OpenAI/LLM ist standardmäßig aktiviert (`ENABLE_LLM` default: `true`). Bei Bedarf kann es mit `ENABLE_LLM=0` deaktiviert werden.
- OpenAI API-Schlüssel wird bevorzugt aus `OPENAI_API_KEY` gelesen.
- OpenAI-Modelle sind jetzt pro Flow getrennt konfigurierbar:
  - `OPENAI_MODEL_PLAN` (Plan-Generierung, Default: `gpt-4o-mini`)
  - `OPENAI_MODEL_EVENTS_FAST` (Eventsuche „schnell“, Default: `gpt-4o-mini`)
  - `OPENAI_MODEL_EVENTS_ACCURATE` (Eventsuche „genau“, Default: `o3-mini`)
- Fallback: Streamlit Secrets in `.streamlit/secrets.toml` im Format:

```toml
[openai]
api_key = "<dein-key>"
```

Beim App-Start wird der Wert aus den Secrets automatisch auf das Runtime-Feld `openai_api_key` gemappt (mit Fallback für alte Env-Key-Namen), falls die Umgebungsvariable fehlt.

Für Docker-Setups liegt die Datei standardmäßig unter `secrets/secrets.toml`; `docker-compose.yml` mountet diesen Pfad zusätzlich nach `/app/.streamlit/secrets.toml`, damit Streamlit-Secrets zuverlässig erkannt werden.

Beim Start werden die Runtime-Settings jetzt über Pydantic Settings geladen und validiert. Wenn `ENABLE_LLM=true` gesetzt ist und kein API-Key vorhanden ist, zeigt die App eine klare zweisprachige Fehlermeldung (DE/EN) und stoppt sicher, statt mit einem Laufzeitfehler weiterzumachen.

- Standort für Wetterabfrage per Umgebungsvariablen konfigurierbar:

```bash
export WEATHER_LAT="51.2149"   # Default: Volksgarten
export WEATHER_LON="6.7861"    # Default: Volksgarten
```

Wenn `WEATHER_LAT`/`WEATHER_LON` nicht gesetzt sind, nutzt die App automatisch Volksgarten-Koordinaten.
Optional kann als Betriebskonvention stattdessen Düsseldorf-Zentrum (`51.2277`, `6.7735`) gesetzt werden.

## Features
- Neuer Offline-Modus (Sidebar-Toggle) für „Wetter & Veranstaltungen“: Die Vorschlagsgenerierung kann vollständig ohne LLM aus einer kuratierten Aktivitätsbibliothek (`data/activity_library.json`) erfolgen; Einträge sind nach Altersbereich, Domain-Tags, Materialien und Safety-Hinweisen strukturiert.
- Offline-Auswahl nutzt jetzt Filter + Scoring, um die 3 besten Bibliothekseinträge zu priorisieren (Age-Fit, Dauer-Fit, Material-Präferenzen via `constraints` mit `material:<name>`), und verankert jede Empfehlung mit einer `library_id` im Begründungs-Payload.
- Neue Material-Checklist (Haushaltsmaterialien) in Sidebar und Formular: Nicht ausgewählte Materialien werden in Vorschlägen/Plänen vermieden; stattdessen erscheinen DE/EN-Ersatzhinweise.
- UI-Texte sind jetzt vollständig auf Deutsch gehalten (keine englischen Textpassagen mehr in der Oberfläche).
- Vor jedem LLM-Aufruf und vor der Ausgabe wird jetzt die OpenAI-Moderation (`omni-moderation-latest`) ausgeführt; bei `flagged=true` blockt die App deterministisch mit einer sicheren DE/EN-Meldung und protokolliert nur metadatenbasierte Events ohne PII.
- OpenAI-Structured-Output-Schema ist jetzt Strict-Mode-kompatibel: URL-Felder in den Activity-Ergebnissen werden als validierte Strings modelliert (ohne `format: "uri"`), um API-Schemafehler zu vermeiden.
- Activity-Search-Datenvertrag erweitert: `ActivitySearchCriteria` verwendet jetzt stabile Contract-Felder `plz`, `radius_km`, `date`, `time_window`, `effort`, `budget_eur_max`, `topics` sowie strikt validierte Vorschlags- und Planmodelle.
- Konsolidierter Such-Contract mit einer Quelle der Wahrheit in `src/mikroabenteuer/models.py`; App, Recommender, Export und Scheduler verwenden konsistente Feldnamen inkl. `topics`-Normalisierung und `time_window`-Ableitung.
- Alterspropagation im Daily-Flow vervollständigt: `child_age_years` ist jetzt Teil von `ActivitySearchCriteria` und wird konsistent von UI → Recommender → Plan-Generierung genutzt; dadurch greifen Altersfilter und Safety-Regeln (z. B. Kleinteile < 3 Jahre) verlässlich.
- Neu strukturierte, zweisprachige Landingpage (DE/EN) mit klarer Hierarchie: Hero, 3-Schritte-Orientierung, Filterbereich, Karten und kompakter Abschluss
- Reduzierte Hero-Sektion mit primärem CTA („Jetzt Abenteuer auswählen / Pick an adventure now") und direktem Scroll-Hinweis
- Kompakter Orientierungskasten „So funktioniert's / How it works" für schnellen Einstieg
- Filterbare Abenteuerkarten nach Jahreszeit, Dauer, Alter und Stimmung inkl. „Details ansehen“-CTA je Karte
- Straffere Nutzenargumentation („Warum das gut tut / Why this helps") und vereinfachter Abschlussblock ohne zusätzliche Lead-Stufen
- Wetterbasierte Abenteuerauswahl mit Volksgarten-Fokus (Open-Meteo)
- Täglicher Scheduler (`08:20`, Europe/Berlin) für Abenteuer-Mail
- RFC-konformer ICS-Builder für Kalendereinladungen
- HTML-Mail-Template mit Inline-CSS (DE/EN)
- Gmail-Versand mit HTML + ICS Attachment
- Wiederholversuche mit exponentiellem Backoff für externe Calls
- Regelbasierter physischer Sicherheits-Validator blockiert unsichere Tagespläne (z. B. Kleinteile <3 Jahre, scharfe Werkzeuge, Feuer/Hitze, Chemikalien) und erzwingt bei Verstoß einen sicheren Fallback-Plan.
- Sicherheitsregel für Scherenmaterial verfeinert: „Schere/scissors" ist nicht mehr pauschal verboten; für Kinder unter 6 Jahren ist Schere nur mit explizitem Kontext „Kinderschere / safety scissors" und „unter Aufsicht / under supervision" zulässig.
- Kalenderähnlicher Bereich mit **Abenteuer des Tages**
- In der Tagesansicht wurde die Überschrift "Motivations‑One‑Liner" entfernt; der Motivationssatz bleibt ohne zusätzliche Zwischenüberschrift sichtbar.
- Aufklappbare Liste (Drop-down/Expander) aller Abenteuer ohne zusätzliche Tabelle
- Helles, kontrastreiches UI-Theme mit `Hintergrund.png` als App-Hintergrund
- Verbesserte Kontraste in Export- und Aktions-Elementen: Download-/Action-Buttons sowie die E-Mail-Vorschau sind jetzt ohne Hover gut lesbar.
- E-Mail-Vorschau im Export zeigt jetzt standardmäßig das gerenderte Layout (statt primär Roh-HTML); der HTML-Quelltext bleibt optional über einen separaten Aufklapper verfügbar.
- Zentrales Begrüßungsbild aus lokalem Asset (`ChatGPT Image 14. Feb. 2026, 20_05_20.png`) im oberen Bereich der Landing-Page, stabil über `st.image` eingebunden
- Hero-Bereich mit zentrierter, zweisprachiger Headline „Miri & Carla: Kleine Abenteuer. Große Erinnerungen 🎂 / Miri & Carla: Small adventures. Big memories.“ direkt oberhalb des Begrüßungsbildes
- Detailansicht pro Abenteuer über `st.expander`
- Neues naturverbundenes Farbkonzept in der UI (Primary Dark Green, Mint, Terracotta, Marigold, Sky Blue, Lavender, Cream, Charcoal) für klare visuelle Hierarchie und bessere Lesbarkeit.
- Neue Sektion „Wetter & Events / Weather & Events“ mit validierten Suchkriterien, orchestrierter Event-Recherche und Darstellung von Wetter, Warnungen, Treffern und Quellen.
- Formulareingaben sind stärker eingeschränkt: Altersband, Zeitbudget, Ortspräferenz, Ziele und Rahmenbedingungen nutzen primär Dropdowns/Toggles/Slider; Freitext ist optional, zeichenbegrenzt und wird vor Validierung bereinigt.
- Sidebar-Filter und „Wetter & Events“-Formular verwenden getrennte Criteria-States (`st.session_state["criteria_daily"]` und `st.session_state["criteria_events"]`), damit Formular-Suchen nicht mehr von Sidebar-Werten überschrieben werden.
- Event-Suchergebnisse bleiben jetzt über Streamlit-Reruns sichtbar: Ergebnisse werden in `st.session_state["events_payload"]` + `events_fingerprint` persistiert und können über „Neu suchen / Search again“ oder „Ergebnisse löschen / Clear results“ gesteuert werden.
- Die Widget-State-Synchronisierung nutzt weiterhin ein einheitliches Criteria↔UI-Mapping mit UI-Adaptern je Bereich (Sidebar/Form), schreibt jedoch jeweils nur in den zuständigen State (`criteria_daily` bzw. `criteria_events`).
- Importvertrag für Wetter-&-Events-Module stabilisiert: `src/mikroabenteuer/openai_activity_service.py` und `src/mikroabenteuer/activity_orchestrator.py` verwenden jetzt paketlokale Relative-Imports auf `src/mikroabenteuer/models.py` statt kollidierender Root-Pfade.
- Variante-A-Importlayout (`src` als kanonischer Runtime-Root) vervollständigt: fehlende `src`-Module `openai_settings.py` und `retry.py` wurden ergänzt, damit `src.mikroabenteuer.*` ohne Fallback auf das Root-Paket importierbar bleibt.
- `ActivitySearchCriteria` wurde um `max_suggestions` + `to_llm_params()` erweitert; ergänzende Ergebnis-/Wettermodelle (`ActivitySuggestionResult`, `SearchStrategy`, `WeatherSummary`) sind nun kanonisch in `src/mikroabenteuer/models.py` definiert.
- `to_llm_params()` liefert nun zusätzlich `available_minutes`; `ActivitySuggestion` deckt den Orchestrator-Vertrag mit `end_time`, `location` und `description` vollständig ab.
- Paketstruktur final vereinheitlicht: `src` ist jetzt explizit als Top-Level-Paket markiert (`src/__init__.py`), damit `src.mikroabenteuer.*` der eindeutige, kanonische Importpfad bleibt.
- Neuer Strukturtest stellt sicher, dass alle `from .xyz import ...`-Referenzen in `src/mikroabenteuer/` auf tatsächlich vorhandene Module zeigen und keine Legacy-Root-Imports (`mikroabenteuer.*`) mehr in diesem Paket verwendet werden.

- Sidebar enthält jetzt ein Familienprofil mit Feldern für **Name des Kindes / Child name**, **Name der Eltern / Parent name(s)** und **Alter des Kindes (Jahre) / Child age (years)**; diese Werte personalisieren Titel, Abenteuertexte und Exporte zur Laufzeit.
- Neue PII-Redaction vor allen OpenAI-Requests: Namen, E-Mail-Adressen, Telefonnummern und adressähnliche Angaben werden vor Moderation/Responses-Aufrufen automatisch maskiert (`redact_pii`), damit keine Roh-PII an LLM-Endpunkte oder Logs gelangt.
- OpenAI-Aufrufe sind jetzt gegen temporäre API-Fehler abgesichert: exponentielles Backoff-Retry greift nur bei 429/5xx/Timeout-Indikatoren; bei endgültigem Fehlschlag werden sichere kuratierte Fallback-Antworten geliefert (kein App-Crash).
- Im Familienprofil zeigt die Sidebar jetzt den Hinweis: „Bitte gib nicht den vollständigen Namen deines Kindes oder identifizierende Informationen ein. / Don’t enter your child's full name or identifying info.“
- Neue strukturierte Planungsmodelle: `ActivityRequest` (Alter in Monaten/Jahren, Dauer, Indoor/Outdoor, Materialien, Ziele, Constraints) und `ActivityPlan` (Schritte, Sicherheitsnotizen, Eltern-Kind-Impulse, Varianten, **What this supports / Was das fördert**); die Tagesansicht rendert aus `ActivityPlan` und zeigt bei LLM-Fehlern eine freundliche Fallback-Meldung mit sicherem Plan.
- Entwicklungsziele sind jetzt als feste Domains modelliert (`gross_motor`, `fine_motor`, `language`, `social_emotional`, `sensory`, `cognitive`); im UI werden 1–2 Ziele gewählt und in die Plan-Generierung inkl. Eltern-Kind-Impulse übernommen.
- Jede Aktivität enthält jetzt verbindlich 3–6 kurze **Say/Do**-Impulse für responsive Austauschmomente; auch Fallback- und Safe-Pläne erzwingen dieses Format statt reiner Anweisungen.
- Neue Aktion „Plan melden / Report plan“ in der Tagesansicht: Für jeden generierten Plan kann jetzt ein Report mit minimalen Metadaten gespeichert werden (UTC-Zeitstempel, Plan-Hash, Grund) – ohne Nutzer-PII.
- Neuer Plan-Modus „Elternskript (kurz, wiederholbar) / Parent script (short, repeatable)“ in der Sidebar: erzeugt ein kindgeführtes, zeitlich begrenztes 4-Schritte-Skript (Describe, Imitate, Praise, Active listening) mit Minimal-Vorbereitung.
- Tagespläne ergänzen jetzt automatisch „Plan B“-Varianten für **lower energy**, **higher energy**, **indoor swap** und **no materials** (zweisprachig DE/EN), damit pro Aktivität direkt Alternativen verfügbar sind.
- Neuer Review-Expander „Gemeldete Pläne ansehen / Review reported plans“ zeigt lokal gespeicherte Meldungen aus `data/plan_reports.jsonl` (oder `PLAN_REPORTS_PATH`).

## Daily Scheduler aktivieren
Der Scheduler wird nur gestartet, wenn die Umgebungsvariable gesetzt ist:

```bash
export ENABLE_DAILY_SCHEDULER=1
```

## Gmail Setup (OAuth)
Benötigte Umgebungsvariablen:

```bash
export DAILY_MAIL_TO="you@example.com"
export DAILY_MAIL_FROM="you@example.com"
export GOOGLE_CLIENT_SECRET_FILE="secrets/client_secret.json"
export GOOGLE_TOKEN_FILE="secrets/token.json"
# LLM safety/rate limits
export MAX_INPUT_CHARS="4000"
export MAX_OUTPUT_TOKENS="800"
export TIMEOUT_S="45"
export MAX_REQUESTS_PER_SESSION="10"
```

Erforderliche Google Redirect URI (Production):

```text
https://yourdomain.de/oauth2callback
```


## Google OAuth2 Setup (Calendar + Gmail)
1. In Google Cloud: create **OAuth consent screen** as `External`.
   - App name: `Miris Mikroabenteuer mit Carla`
   - Support email: `gerrit.fabisch2024@gmail.com`
   - Test user: `gerrit.fabisch2024@gmail.com`
2. Add least-privilege scopes:
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
3. Create OAuth client as **Desktop App** and download JSON to:
   - `secrets/google_client_secret.json` (never commit)
4. OAuth token is generated and stored locally in:
   - `secrets/token.json` (never commit)

Die App nutzt die gleichen Credentials für Kalender-Events und Gmail-Versand.
The app uses the same credentials for calendar event creation and Gmail sending.

## Secrets & Token Storage
- Development: store OAuth files in `secrets/`.
- Production (recommended): store encrypted token/client secret in GCP Secret Manager or base64-encoded environment variables.
- Never store secrets in the repository and never log token payloads.

## Docker Deployment

```bash
docker compose up --build
```

## Nginx Reverse Proxy (HTTPS)
Minimalbeispiel:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.de;

    location / {
        proxy_pass http://localhost:8501;
    }
}
```

## Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Abhängigkeiten / Dependencies
- `pydantic` ist auf `>=2.6,<3` begrenzt, damit in Deployments (z. B. Streamlit Cloud) stabil Pydantic v2 aufgelöst wird.
- `pydantic` is constrained to `>=2.6,<3` so deployments (e.g., Streamlit Cloud) consistently resolve Pydantic v2.


## App starten
```bash
streamlit run app.py
```

## Landingpage-Screenshot
- Aktuelle Landingpage-Struktur: `browser:/tmp/codex_browser_invocations/d8cd397d06237a46/artifacts/images/landingpage-struktur.png`

## Tests
```bash
pytest -m "not integration"
ruff format && ruff check
mypy .
```

## Security-Hinweise
- Tokens in `secrets/` Volume speichern (nicht ins Image einbauen)
- Nur minimale OAuth-Scopes verwenden (`calendar.events`, `calendar.readonly`, `gmail.send`)
- Keine API-Keys oder PII loggen
- Externe Requests mit Timeouts + Backoff absichern

## Neu: Vollständige `src/mikroabenteuer`-Integration in der Landing-Page
- Die Landing-Page nutzt jetzt direkt die neuen Module aus `src/mikroabenteuer` (Konfiguration, Seed-Daten, Wetter, Recommender, OpenAI-Generierung).
- Daily-Ansicht unterstützt Export als JSON, Markdown und ICS.
- Optionaler Automation-Block erlaubt das manuelle Auslösen des Daily-Jobs (inkl. optionalem Gmail-/Calendar-Flow bei vorhandenen OAuth-Credentials).
- Bei KI-Generierung werden verständliche Fehlhinweise und automatische Wiederholversuche mit exponentiellem Backoff verwendet.
- Neue UI-Texte sind weiterhin DE/EN gehalten.


## Änderungen (letzte Updates)
- DE: UI-Entrümpelung: Die Überschrift "Plan (kurz & klar)" wurde zu "Plan" vereinfacht; ergänzende Filter-Hinweise in Sidebar und „Wetter & Veranstaltungen“ wurden entfernt.
- EN: UI cleanup: The heading "Plan (kurz & klar)" was simplified to "Plan"; extra filter hints in the sidebar and the “Weather & Events” section were removed.
- DE: Der Block "Mikroabenteuer des Tages 🌿" zeigt standardmäßig nur Titel, Abenteuername, Ort/Dauer/Distanz und Wetter; alle weiteren Inhalte sind initial eingeklappt über einen Details-Expander.
- EN: The "Mikroabenteuer des Tages 🌿" block now shows only title, adventure name, location/duration/distance, and weather by default; all remaining content is initially collapsed behind a details expander.
- DE: In der Tagesansicht gibt es jetzt die Aktion „Plan melden / Report plan" mit Gründen-Auswahl; gespeichert werden nur UTC-Zeitstempel, Plan-Hash und Grund in einer lokalen Report-Datei (keine Nutzer-PII).
- EN: The daily view now includes a "Plan melden / Report plan" action with reason selection; only UTC timestamp, plan hash, and reason are stored in a local report file (no user PII).
