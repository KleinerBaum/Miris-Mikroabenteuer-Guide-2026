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

## Features
- Wetterbasierte Abenteuerauswahl für Düsseldorf (Open-Meteo)
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

## Tests
```bash
pytest -m "not integration"
ruff format && ruff check
mypy .
```

## Security-Hinweise
- Tokens in `secrets/` Volume speichern (nicht ins Image einbauen)
- Nur minimale OAuth-Scopes verwenden (`gmail.send`)
- Keine API-Keys oder PII loggen
- Externe Requests mit Timeouts + Backoff absichern
