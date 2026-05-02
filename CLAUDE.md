# PaceForge

AI-enhanced running plan generator for Garmin watches. Python 3.11+ / FastAPI / Streamlit / Expo React Native.

## Commands

```bash
pip install -e ".[dev]"              # Install with dev deps
ruff check src/ tests/               # Lint (must pass before commit)
pytest tests/ -x --tb=short          # Tests (must pass before push)
uvicorn paceforge.api.app:app --reload   # API on :8000
streamlit run src/paceforge/dashboard.py # Dashboard on :8501
cd mobile && npm ci && npx expo start    # Mobile app
```

## Architecture

- **`api/app.py`** — monolithic FastAPI (~3500 lines). All endpoints in one file, grouped by `# ── Section ──` comments. Auth via `Depends(get_current_user)` on every protected endpoint.
- **`dashboard.py`** — monolithic Streamlit (~6500 lines). 8 tabs + admin panel. API calls via `requests` to `http://localhost:8000` with `_auth_headers()`.
- **`auth/database.py`** — SQLite with thread lock, WAL mode. User data stored as JSON blobs. Migrations via `ALTER TABLE ADD COLUMN` with `try/except`.
- **`ai/coach.py`** — LLM integration (gpt-4o-mini). JSON responses parsed with `json.loads()` + `json_repair` fallback. Always validate/backfill AI output.
- **`engine/`** — VDOT calculator, plan generator, workout templates.
- **`models/`** — Pydantic v2 models. Use `model_dump(mode="json")` / `model_validate_json()`.
- **`mobile/`** — Expo SDK 54 / React Native app (TypeScript).

## Style

- Ruff, 100-char line length. See `pyproject.toml` `[tool.ruff.lint]` for rules.
- `from __future__ import annotations` at top of every module.
- `contextlib.suppress()` over bare `try/except/pass`.
- Commit messages: `area: short description` (e.g. `diet: backfill missing meal types`).

## Gotchas

- `app.py` and `dashboard.py` are very large single files. Navigate by section headers.
- AI/LLM output is unreliable — always backfill missing fields, never trust counts.
- SQLite `user_data` columns are JSON blobs (`plan_json`, `activities_json`, `diet_json`, `health_json`, etc.).
- `.db` files are gitignored. Docker uses `/home/data/paceforge.db` for persistence.
- `E402` import rule is ignored — some imports are deferred after config setup.
- `streamlit-calendar`: must pass `callbacks=["eventClick", "eventChange"]` — never include `eventsSet` (fires every rerender, overwrites click/drag events).
- Training paces in dashboard are editable `st.text_input` fields showing `M:SS` format. Session state keys: `pace_{plan_id}_{key}` (e.g. `pace_abc123_easy_pace`). Parsed to seconds when sent to `/plan/adapt`.
- `/plan/adapt` preserves `plan.accepted` state — never reset it to `False` after adaptation.
- `adapt_plan()` in `engine/adaptation.py` accepts optional `custom_paces` dict. When provided, manual paces override VDOT auto-calculation.
