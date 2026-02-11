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
