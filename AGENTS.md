# AGENTS.md (Scope: gesamtes Repository)

## Purpose
Operational rules for Codex Cloud contributors in this repository.

## Quick defaults
- Language for code: Python >= 3.11
- Style: PEP 8 + type hints required
- Keep changes minimal, focused, and reversible
- Prefer static analysis first; run commands only when needed

## Branching & PR
- Create feature branches as: `feat/<kurz-beschreibung>`
- Open PRs against `dev`
- Merge to `main` only via merge train from `dev`
- Every PR must include Release Notes section

## Required checks before merge (CI-blocking)
Run and ensure green:
1. `ruff format && ruff check`
2. `mypy` (no new type errors)
3. `pytest -m "not integration"` (all unit tests passing)

## Documentation & i18n
For every functional change:
- Update `README` and `CHANGELOG`
- New UI text must be bilingual (EN + DE)
- If UI is affected, refresh screenshots in `images/`

## Schema propagation rule (CS_SCHEMA_PROPAGATE)
If a data field/schema changes, update consistently in:
- schema
- business logic
- UI
- export layer
Also:
- document mapping/migration changes
- adapt/add tests

## LLM/API usage
- Use OpenAI Responses API with tools (`WebSearchTool`, `FileSearchTool`)
- Require structured outputs (Pydantic models or valid JSON)
- Default model: `gpt-4o-mini`
- “Genau”-mode: higher model (e.g. `o3-mini`) respecting `REASONING_EFFORT`
- Respect configured timeouts
- Optional EU base URL allowed: `https://eu.api.openai.com/v1`

## Retrieval (RAG)
- If `VECTOR_STORE_ID` is set: use OpenAI Vector Store Search
- Otherwise continue without document retrieval

## ESCO API
- Allow only GET requests to `https://ec.europa.eu/esco/api`
- Cache responses via `st.cache_data` with explicit TTL

## UX smoke test (after changes)
Verify manually:
- Wizard flow
- Summary view
- Export formats (JSON + Markdown)
- Boolean-string generator

## Security & secrets
- Never log PII or API keys
- Read `OPENAI_API_KEY` only via `os.getenv` or `st.secrets`
- Never hardcode secrets
- Keep internet access disabled by default for agent tasks
- If internet is needed, restrict domains + HTTP methods

## Collaboration protocol for Codex
When creating tasks for the agent, include:
- concrete file paths / IDs
- reproduction steps
- commands used
- full output of failing commands

## Output format expectations (for agent responses)
- concise summary
- changed files
- commands run + outcomes
- open risks / follow-ups
