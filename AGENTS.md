# PaceForge — Agent Instructions

Single-user, serverless running coach. No backend, no database, no LLM API key.
**Claude is the coach** (`.claude/skills/coach/`); the `paceforge` package does the
deterministic maths + Garmin/Strava I/O; `data/*.json` (git-tracked) is the state.

Full orientation is in [CLAUDE.md](CLAUDE.md) — read it. Key points:

## Architecture
```
src/paceforge/
├── store.py          # load/save data/*.json (the "database")
├── actions.py        # all behaviour; CLI + MCP are thin wrappers over this
├── cli.py            # `paceforge` command
├── mcp_server.py     # `paceforge-mcp` stdio server (Claude desktop)
├── engine/           # vdot, workouts, planner (LLM-free), adaptation,
│                     # analytics (health/running analysis), validate (rule checks)
├── garmin/client.py  # reads metrics, uploads structured workouts (garth)
├── strava/client.py  # OAuth + activity push
└── hyrox/            # race-result analyzer vs field benchmarks
data/*.json           # profile.json, plan.json, activities.json
```

## The AI / validation split
Deterministic facts (paces, plan structure) stay in code. Claude **proposes** a plan
(scaffold with `paceforge plan`, then personalise), `engine/validate.py` **checks** it.
Never invent paces — the engine derives them.

## Commands
```bash
.venv/bin/ruff check src/ tests/    # lint (must pass before commit)
.venv/bin/pytest tests/ -q          # tests (must pass before push)
.venv/bin/paceforge sync|analyze|plan|validate|push|status
```

## Conventions
- Python 3.11+, ruff 100-char lines, `from __future__ import annotations` at top.
- One behaviour module (`actions.py`) — keep CLI/MCP as thin wrappers, no duplicated logic.
- Commit messages: `area: short description`. Run ruff + pytest before committing.
