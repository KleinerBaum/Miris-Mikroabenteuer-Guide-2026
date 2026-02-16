# README.md

# 🌿 Miris Mikroabenteuer Guide 2026

[![CI](https://github.com/KleinerBaum/Miris-Mikroabenteuer-Guide-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/KleinerBaum/Miris-Mikroabenteuer-Guide-2026/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Eine **Streamlit-Webapp**, die täglich (und filterbar) **Mikroabenteuer** vorschlägt und daraus auf Wunsch einen **sicheren, strukturierten Activity-Plan** erzeugt – gedacht für **Miri (Mama) & Carla (Kind)**, standardmäßig rund um **Düsseldorf (Volksgarten/Südpark)**.

Die App kann:
- **ohne LLM** (offline/curated) laufen,
- optional mit **OpenAI Responses API** + **Structured Output** + **Moderation** + **PII-Redaction** arbeiten,
- Markdown/JSON/ICS exportieren,
- optional per OAuth **Gmail** senden / **Google Calendar** Events anlegen.

---

## Highlights

- **Seed-Bibliothek** (kuratierte Mikroabenteuer) + Filter & Ranking  
  → `src/mikroabenteuer/data_seed.py`, `src/mikroabenteuer/recommender.py`
- **Wetter** (Open‑Meteo, ohne API-Key)  
  → `src/mikroabenteuer/weather.py`
- **“Wetter & Events”**: Web‑Recherche über OpenAI `web_search` Tool (optional) + Offline‑Fallback  
  → `src/mikroabenteuer/openai_activity_service.py`, `src/mikroabenteuer/activity_orchestrator.py`
- **LLM-Planung als Schema** (`ActivityPlan`) + Safety‑Validator + “Plan B” Varianten  
  → `src/mikroabenteuer/openai_gen.py`, `src/mikroabenteuer/models.py`
- **Privacy & Safety**: PII‑Redaction vor Requests, Moderation vor/nach LLM  
  → `src/mikroabenteuer/pii_redaction.py`, `src/mikroabenteuer/moderation.py`
- **Plan melden** (ohne PII): speichert nur Hash + Grund + UTC‑Zeit  
  → `src/mikroabenteuer/plan_reports.py` (default: `data/plan_reports.jsonl`)
- **CI & Pre‑commit**: ruff + pytest + detect-secrets  
  → `.github/workflows/ci.yml`, `.pre-commit-config.yaml`
- **Verbesserte Lesbarkeit in der UI / Improved UI readability**: überarbeitetes Farbschema für Form-Controls (Inputs, Selects, Slider, Tags) mit höherem Kontrast.  
  → `app.py`

---

## Architekturstatus (wichtig)

Aktuell gibt es **zwei Codebasen**:

- **V2 (aktiv):** `src/mikroabenteuer/*`  
  Wird von `app.py` genutzt, enthält die aktuellen Pydantic‑Schemas, LLM‑Structured Outputs etc.
- **V1 (legacy):** `mikroabenteuer/*` (Repo-Root)  
  Ältere Implementationen (YAML Seed, legacy Engine, legacy ICS/Google).  
  Einige Tests referenzieren V1 noch.

👉 **Neue Entwicklung bitte in V2 (`src/mikroabenteuer`) machen.**  
Eine Konsolidierung zu einem “normalen” `src`‑Layout (ohne `src.mikroabenteuer`‑Importprefix) ist geplant und in `CHANGELOG.md` unter **Unreleased** beschrieben.

---

## Quickstart (lokal)

### 1) Setup

```bash
git clone https://github.com/KleinerBaum/Miris-Mikroabenteuer-Guide-2026.git
cd Miris-Mikroabenteuer-Guide-2026

python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
