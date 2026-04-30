# PaceForge — Agent Instructions

## Project Overview

AI-enhanced running plan generator for Garmin watches. Analyses Garmin Connect fitness data and generates personalised training plans. See [README.md](README.md) for full feature list.

## Architecture

```
src/paceforge/
├── api/app.py         # FastAPI monolith — ALL endpoints (~3500 lines)
├── ai/coach.py        # OpenAI/Anthropic LLM integration (gpt-4o-mini default)
├── auth/              # JWT auth (HS256), SQLite user DB, bcrypt passwords
├── engine/            # VDOT calculator, plan generator, workout templates
├── garmin/client.py   # Garmin Connect API wrapper (activities, workouts)
├── hyrox/             # HYROX race result scraper + analyser
├── models/            # Pydantic v2 data models (plan, profile, diet)
├── strava/client.py   # Strava OAuth integration
├── dashboard.py       # Streamlit frontend (~6500 lines, single file)
└── mobile_web/        # SPA served at /m/ with nginx user-agent redirect
mobile/                # Expo SDK 54 / React Native 0.81.5 app (TypeScript)
```

### Key patterns

- **Single-file API**: All FastAPI endpoints live in `api/app.py`. Endpoints are grouped by comment sections (`# ── Section ──`). New endpoints go in the matching section.
- **Single-file dashboard**: All Streamlit UI lives in `dashboard.py`. Tabs are indexed from `tabs[]` and sections use `with tab_xxx:` blocks.
- **SQLite persistence**: `auth/database.py` manages schema + migrations. User data stored as JSON blobs in `user_data` table columns (`plan_json`, `activities_json`, `diet_json`, etc.). Migrations are `ALTER TABLE ADD COLUMN` with `try/except` for idempotency.
- **AI responses**: LLM calls return JSON strings parsed with `json.loads()`, with `json_repair` as fallback. Always validate/backfill AI output — the model frequently omits fields or skips items.
- **Pydantic v2**: All models use `BaseModel` with `model_dump(mode="json")` / `model_validate_json()`. No v1 patterns.
- **Config**: `pydantic-settings` with `PACEFORGE_` env prefix. See [.env.example](.env.example).

## Commands

```bash
# Install
pip install -e ".[dev]"

# Lint (must pass before commit)
ruff check src/ tests/

# Tests (must pass before push)
pytest tests/ -x --tb=short

# Run locally
uvicorn paceforge.api.app:app --reload          # API on :8000
streamlit run src/paceforge/dashboard.py         # Dashboard on :8501

# Mobile
cd mobile && npm ci && npx expo start
```

## Code Style

- Python 3.11+, ruff with 100-char line length
- See [pyproject.toml](pyproject.toml) `[tool.ruff.lint]` for full rule config
- `from __future__ import annotations` at top of modules
- FastAPI `Depends(get_current_user)` for auth — never skip on new endpoints
- Use `contextlib.suppress()` over bare `try/except/pass`
- Imports: `E402` is ignored — some imports are intentionally deferred after config

## CI/CD

- **CI** ([.github/workflows/ci.yml](.github/workflows/ci.yml)): ruff + pytest on Python 3.11 & 3.12, TypeScript check for mobile
- **CD** ([.github/workflows/cd.yml](.github/workflows/cd.yml)): `az acr build` → `az webapp restart`
- Branch: `master` only
- Docker base: custom Oryx image in ACR. See [Dockerfile](Dockerfile)
- Azure: App Service B1 Linux, ACR `paceforgeacr`, port 80 (nginx → uvicorn:8000 + streamlit:8501)

## Conventions

- **Always run `ruff check src/ tests/` and `pytest tests/ -x` before committing**
- Never push without all tests passing
- Commit messages: `area: short description` (e.g., `diet: backfill missing meal types`)
- `.db` files are gitignored
- Dashboard API calls go through `_auth_headers()` helper and local `requests` to FastAPI
