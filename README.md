# Miris-Mikroabenteuer-Guide-2026

Eine lokale Streamlit-MVP-App für "Mikroabenteuer mit Carla" – erweitert um Daily-Automation als SaaS-Basis.

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
- Conversion-orientierte, zweisprachige Landingpage (DE/EN) im Funnel-Aufbau: Aufmerksamkeit → Relevanz → Vertrauen → Auswahl → Handlung
- Hero-Sektion mit klaren CTA-Pfaden („Jetzt Mikroabenteuer entdecken“, „Nach Jahreszeit filtern")
- CTA-Buttons im Hero-Bereich in dunklem Grau mit weißer Schrift für besseren Kontrast und ruhigeres Erscheinungsbild
- Problem-/Lösungssektion, Mikroabenteuer-Erklärung, Wirkungsargumentation und 3-Schritte-Startformel
- Filterbare Abenteuerkarten nach Jahreszeit, Dauer, Alter und Stimmung inkl. „Details ansehen“-CTA je Karte
- Lead-Element für kostenlose Ideenliste und emotionaler Abschluss-CTA für Wiederkehr/Start
- Wetterbasierte Abenteuerauswahl mit Volksgarten-Fokus (Open-Meteo)
- Täglicher Scheduler (`08:20`, Europe/Berlin) für Abenteuer-Mail
- RFC-konformer ICS-Builder für Kalendereinladungen
- HTML-Mail-Template mit Inline-CSS (DE/EN)
- Gmail-Versand mit HTML + ICS Attachment
- Wiederholversuche mit exponentiellem Backoff für externe Calls
- Kalenderähnlicher Bereich mit **Abenteuer des Tages**
- Aufklappbare Liste (Drop-down/Expander) aller Abenteuer ohne zusätzliche Tabelle
- Helles, kontrastreiches UI-Theme mit `Hintergrund.png` als App-Hintergrund
- Zentrales Begrüßungsbild aus lokalem Asset (`20251219_155329.jpg`) im oberen Bereich der Landing-Page, stabil über `st.image` eingebunden
- Hero-Bereich mit zentrierter, zweisprachiger Headline „Kleine Abenteuer. Große Erinnerungen 🎂 / Small adventures. Big memories.“ direkt oberhalb des Begrüßungsbildes
- Detailansicht pro Abenteuer über `st.expander`

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
   - App name: `Mikroabenteuer mit Carla`
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

## App starten
```bash
streamlit run app.py
```

## Landingpage-Screenshot
- Aktuelle Funnel-Landingpage: `browser:/tmp/codex_browser_invocations/405e90d1146ed5ee/artifacts/landingpage-funnel-firefox.png`

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
