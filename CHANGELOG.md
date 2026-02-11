# Changelog

## Unreleased

### Geändert / Changed
- DE: `mikroabenteuer/ui/__init__.py` ergänzt und Package-Imports auf relative Importe umgestellt, um sporadische `KeyError`-Importprobleme in Streamlit-Reloadern zu vermeiden.
- EN: Added `mikroabenteuer/ui/__init__.py` and switched package internals to relative imports to prevent intermittent `KeyError` import failures during Streamlit reloads.


### Hinzugefügt
- OpenAI-API-Schlüssel-Auflösung über `OPENAI_API_KEY` mit Streamlit-Secrets-Fallback (`[openai].api_key`) ergänzt.
- OpenAI-Schlüsselkonfiguration beim App-Start integriert und Unit-Tests für die Schlüsselauflösung ergänzt.
- Initiales Streamlit-MVP mit Abenteuer des Tages, Übersichtstabelle und detaillierten Abenteuerkarten hinzugefügt.
- Wiederverwendbares Pydantic-Datenmodell für Abenteuer und Sicherheitsprofil ergänzt.
- Laden von YAML-Seed-Daten und grundlegender Unit-Test für Modellvalidierung ergänzt.
- Updated landing page design with `Hintergrund.png` as a light app background and adjusted color styling for readability.
- Added centered hero welcome image (`20251219_155329.jpg`) at the top of the landing page.
- Added OpenAI API key resolution via `OPENAI_API_KEY` with Streamlit secrets fallback (`[openai].api_key`).
- Wired OpenAI key configuration at app startup and added unit tests for key resolution.
- Initial Streamlit MVP with adventure of the day, overview table, and detailed adventure cards.
- Reusable Pydantic data model for adventures and safety profile.
- YAML seed data loading and basic unit test for model validation.