# Changelog

## Unreleased

### Added
- Added OpenAI API key resolution via `OPENAI_API_KEY` with Streamlit secrets fallback (`[openai].api_key`).
- Wired OpenAI key configuration at app startup and added unit tests for key resolution.
- Initial Streamlit MVP with adventure of the day, overview table, and detailed adventure cards.
- Reusable Pydantic data model for adventures and safety profile.
- YAML seed data loading and basic unit test for model validation.
