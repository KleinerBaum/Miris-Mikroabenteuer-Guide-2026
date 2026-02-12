# 🌿 Mikroabenteuer mit Carla

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
- OpenAI API-Schlüssel wird bevorzugt aus `OPENAI_API_KEY` gelesen.
- Fallback: Streamlit Secrets in `.streamlit/secrets.toml` im Format:

```toml
[openai]
api_key = "<dein-key>"
```

Beim App-Start wird der Wert aus den Secrets automatisch als `OPENAI_API_KEY` gesetzt, falls die Umgebungsvariable fehlt.

- Standort für Wetterabfrage per Umgebungsvariablen konfigurierbar:

```bash
export WEATHER_LAT="51.2149"   # Default: Volksgarten
export WEATHER_LON="6.7861"    # Default: Volksgarten
```

Wenn `WEATHER_LAT`/`WEATHER_LON` nicht gesetzt sind, nutzt die App automatisch Volksgarten-Koordinaten.
Optional kann als Betriebskonvention stattdessen Düsseldorf-Zentrum (`51.2277`, `6.7735`) gesetzt werden.

## Features
- Activity-Search-Datenvertrag erweitert: `ActivitySearchCriteria` verwendet jetzt stabile Contract-Felder `plz`, `radius_km`, `date`, `time_window`, `effort`, `budget_eur_max`, `topics` sowie strikt validierte Vorschlags- und Planmodelle.
- Konsolidierter Such-Contract mit einer Quelle der Wahrheit in `src/mikroabenteuer/models.py`; App, Recommender, Export und Scheduler verwenden konsistente Feldnamen inkl. `topics`-Normalisierung und `time_window`-Ableitung.
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
- Kalenderähnlicher Bereich mit **Abenteuer des Tages**
- Aufklappbare Liste (Drop-down/Expander) aller Abenteuer ohne zusätzliche Tabelle
- Helles, kontrastreiches UI-Theme mit `Hintergrund.png` als App-Hintergrund
- Verbesserte Kontraste in Export- und Aktions-Elementen: Download-/Action-Buttons sowie die E-Mail-Vorschau sind jetzt ohne Hover gut lesbar.
- Zentrales Begrüßungsbild aus lokalem Asset (`20251219_155329.jpg`) im oberen Bereich der Landing-Page, stabil über `st.image` eingebunden
- Hero-Bereich mit zentrierter, zweisprachiger Headline „Miri & Carla: Kleine Abenteuer. Große Erinnerungen 🎂 / Miri & Carla: Small adventures. Big memories.“ direkt oberhalb des Begrüßungsbildes
- Detailansicht pro Abenteuer über `st.expander`
- Neues naturverbundenes Farbkonzept in der UI (Primary Dark Green, Mint, Terracotta, Marigold, Sky Blue, Lavender, Cream, Charcoal) für klare visuelle Hierarchie und bessere Lesbarkeit.
- Neue Sektion „Wetter & Events / Weather & Events“ mit validierten Suchkriterien, orchestrierter Event-Recherche und Darstellung von Wetter, Warnungen, Treffern und Quellen.
- Importvertrag für Wetter-&-Events-Module stabilisiert: `src/mikroabenteuer/openai_activity_service.py` und `src/mikroabenteuer/activity_orchestrator.py` verwenden jetzt paketlokale Relative-Imports auf `src/mikroabenteuer/models.py` statt kollidierender Root-Pfade.
- Variante-A-Importlayout (`src` als kanonischer Runtime-Root) vervollständigt: fehlende `src`-Module `openai_settings.py` und `retry.py` wurden ergänzt, damit `src.mikroabenteuer.*` ohne Fallback auf das Root-Paket importierbar bleibt.
- `ActivitySearchCriteria` wurde um `max_suggestions` + `to_llm_params()` erweitert; ergänzende Ergebnis-/Wettermodelle (`ActivitySuggestionResult`, `SearchStrategy`, `WeatherSummary`) sind nun kanonisch in `src/mikroabenteuer/models.py` definiert.
- `to_llm_params()` liefert nun zusätzlich `available_minutes`; `ActivitySuggestion` deckt den Orchestrator-Vertrag mit `end_time`, `location` und `description` vollständig ab.
- Paketstruktur final vereinheitlicht: `src` ist jetzt explizit als Top-Level-Paket markiert (`src/__init__.py`), damit `src.mikroabenteuer.*` der eindeutige, kanonische Importpfad bleibt.
- Neuer Strukturtest stellt sicher, dass alle `from .xyz import ...`-Referenzen in `src/mikroabenteuer/` auf tatsächlich vorhandene Module zeigen und keine Legacy-Root-Imports (`mikroabenteuer.*`) mehr in diesem Paket verwendet werden.

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
