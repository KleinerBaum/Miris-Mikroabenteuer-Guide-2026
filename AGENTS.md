# AGENTS.md — Miris-Mikroabenteuer-Guide-2026

Repository-wide operating rules for Codex and contributors.

## Non-negotiables

- Never place secrets, tokens, credentials, PII, or raw provider payloads in code, logs, commits, screenshots, or PR descriptions.
- Keep changes small, reviewable, reversible, and covered by the narrowest useful verification first.
- Preserve the deterministic offline path. OpenAI, weather, event search, Gmail, and Calendar integrations remain optional enhancements.
- Preserve curated safety rules, moderation, PII redaction, age filters, supervision guidance, hazards, mitigations, and stop conditions.
- Keep schema, state, UI, exports, prompts, tests, and documentation synchronized when a contract changes.

## Codex and WSL environment

- Use the native WSL checkout at `/home/gerri/src/github.com/KleinerBaum/Miris-Mikroabenteuer-Guide-2026`; do not operate this repository through `/mnt/c`, `/mnt/wslg/distro`, `\\wsl$`, or Git for Windows.
- Use Python 3.11, matching CI. The checked-in Codex environment creates `.venv` with `uv` and installs runtime plus test tooling.
- Keep `.env` and `.streamlit/secrets.toml` local and ignored. Never print their values.
- Do not deploy, publish, commit, push, or change external services unless the user explicitly requests it.

## Repository map

- `src/mikroabenteuer/` — active V2 package and the destination for new implementation work.
- `legacy/v1/` — legacy implementation; do not add new dependencies on it without an explicit migration task.
- `app.py` and `pages/` — Streamlit entry points.
- `data/activity_library.json` — curated activity source; preserve provenance and safety metadata.
- `tests/` — unit, contract, privacy, resilience, and safety coverage.

## Local commands

The Codex setup action prepares the environment automatically. Manual equivalent:

```bash
uv venv --python 3.11 --allow-existing .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python ruff pytest
```

Run the app:

```bash
.venv/bin/python -m streamlit run app.py
```

## Verification

Run before handoff:

```bash
.venv/bin/python -m ruff format --check .
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -m "not integration"
.venv/bin/python -c "import app"
```

Report exact commands and actual results. Do not claim a check passed unless it ran successfully.

## Working style

- Prefer deterministic domain helpers and cached Streamlit results over UI-only logic.
- Use English technical names and preserve the existing German product copy.
- Add or update regression tests when behavior changes.
- Avoid unrelated formatting churn, broad refactors, dependency additions, or scope expansion.
