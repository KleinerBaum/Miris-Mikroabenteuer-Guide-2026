# Changelog

## Unreleased

### Added
- Added Google OAuth integration scaffold with per-user token storage (`secrets/google_tokens/*.json`) and minimal-privilege scopes for Calendar events and Gmail send.
- Added Google Calendar service wrapper with retry/backoff and event/list helpers.
- Added Gmail service wrapper with HTML email sending, ICS attachment builder, and weather-based Volksgarten recommendation text.
- Added Streamlit UI controls to connect a Google account, create events, and send adventure emails.
- Added dependency pins for Google client libraries and unit tests for token path sanitization, weather suggestions, and ICS generation.
- Added OpenAI API key resolution via `OPENAI_API_KEY` with Streamlit secrets fallback (`[openai].api_key`).
- Wired OpenAI key configuration at app startup and added unit tests for key resolution.
- Initial Streamlit MVP with adventure of the day, overview table, and detailed adventure cards.
- Reusable Pydantic data model for adventures and safety profile.
- YAML seed data loading and basic unit test for model validation.

### Security
- Added `secrets/` to `.gitignore` to prevent committing OAuth tokens/client secrets.
