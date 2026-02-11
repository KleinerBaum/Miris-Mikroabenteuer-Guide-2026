# Miris-Mikroabenteuer-Guide-2026

Eine lokale Streamlit-MVP-App für "Mikroabenteuer mit Carla".

## Konfiguration / Configuration
- OpenAI API-Schlüssel wird bevorzugt aus `OPENAI_API_KEY` gelesen.
- Fallback: Streamlit Secrets in `.streamlit/secrets.toml` im Format:

```toml
[openai]
api_key = "<dein-key>"
```

Beim App-Start wird der Wert aus den Secrets automatisch als `OPENAI_API_KEY` gesetzt, falls die Umgebungsvariable fehlt.

## Features
- Kalenderähnlicher Bereich mit **Abenteuer des Tages**
- Übersichtstabelle aller Abenteuer
- Detailansicht pro Abenteuer über `st.expander`
- Safety-Block pro Abenteuer
- Carla-Entwicklungsvorteil + Carla-Tipp
- Standardisierte Mini-Reiseapotheke
- Wiederverwendbares Pydantic-Datenmodell

## Projektstruktur
```text
mikroabenteuer-mit-carla/
├── app.py
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── mikroabenteuer/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── data_loader.py
│   ├── seed.yaml
│   └── ui/
│       ├── table.py
│       └── details.py
└── tests/
    └── test_models.py
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
```


## Google Calendar + Gmail API Integration (OAuth pro User)

### Ziele / Goals
- Kein UI-Embedding von Google-Produkten, sondern API-basierter Zugriff in der App.
- OAuth pro User mit minimalen Scopes und Token-Speicherung pro User.
- Minimal Privilege: nur `calendar.events`, `calendar.readonly`, `gmail.send` (+ `openid`, `userinfo.email` für stabile User-Zuordnung).

### Google Cloud Setup
1. Projekt `mikroabenteuer-carla` anlegen.
2. APIs aktivieren: Google Calendar API, Gmail API.
3. OAuth Consent Screen (External) konfigurieren.
4. OAuth Client erstellen und `client_secret` als `secrets/google_client_secret.json` speichern.
5. **Authorized redirect URI exakt setzen:** `https://mikrocarla.streamlit.app/`

### Lokale Secrets
- `secrets/` ist in `.gitignore` und darf nie committed werden.
- Token werden pro User in `secrets/google_tokens/<user_key>.json` gespeichert.

### Neue Module
```text
mikroabenteuer/google/
├── __init__.py
├── auth.py
├── calendar_service.py
├── gmail_service.py
└── schemas.py
```

### Features
- OAuth-Verbindung pro User (Connect-Button in der App).
- Kalenderevent-Erstellung für Abenteuer.
- HTML-Mailversand mit Inline-Styles.
- ICS-Attachment-Erzeugung und Versand.
- Wetterbasierte Aktivitätsempfehlung mit Fokus auf Düsseldorf Volksgarten.
- Retry-Logik (exponentielles Backoff) für Google API Calls.

### Daily Scheduler Hinweis
Für produktiven Versand um 08:20 wird ein externer Scheduler empfohlen (z. B. Cloud Scheduler + geschützte Endpoint-Route), der `send_html_email(...)` mit vorbereiteten Nutzdaten triggert.
