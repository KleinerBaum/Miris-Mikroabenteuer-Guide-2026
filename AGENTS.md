
---

```md
# AGENTS.md

# AGENTS.md (Repository scope)

Operational rules for automated agents (Codex) and human contributors.

## Non-negotiables

- **No secrets / tokens / PII** in code, logs, commits, PR descriptions.
- Keep changes **small, reviewable, reversible** (prefer multiple PRs).
- If you change a schema/contract, propagate it everywhere (see CS_SCHEMA_PROPAGATE).
- Prefer **determinism** and **cached results** in Streamlit flows to avoid costly reruns.

---

## Repo map (important)

### Current state: two codebases

- **V2 (active):** `src/mikroabenteuer/*`  
  Used by `app.py` via `from src.mikroabenteuer...` imports.
- **V1 (legacy):** `mikroabenteuer/*` (repo root)  
  Older implementations; some tests still reference it.

✅ New work goes into **V2**.  
⚠️ Do not introduce new dependencies on V1 unless it’s part of the migration plan.

### Planned: consolidation (Option A)
We are moving towards a standard `src` layout where the package is imported as `mikroabenteuer.*` (no `src.` prefix) and V1 is archived under `legacy/`. Track in `CHANGELOG.md → Unreleased`.

---

## Local commands (baseline)

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install ruff pytest
