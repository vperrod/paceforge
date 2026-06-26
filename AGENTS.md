# PaceForge — Agent Instructions

Single-user, serverless running coach. No backend, no database, no LLM API key.
**Claude is the coach** (`.claude/skills/coach/`); the `paceforge` package does the
deterministic maths + Garmin I/O; `data/*.json` (git-tracked) is the state.

Full orientation is in [CLAUDE.md](CLAUDE.md) — read it. Key points:

## Architecture
```
src/paceforge/
├── store.py          # load/save data/* (the "database"): profile, plan, activities,
│                     # details, history, benchmarks, hyrox
├── actions.py        # all behaviour; CLI + MCP are thin wrappers. sync(), analyze(),
│                     # fitness() (Fitness 2.0 assessment), plan/push/validate
├── cli.py            # `paceforge` command
├── mcp_server.py     # `paceforge-mcp` stdio server (Claude desktop)
├── engine/           # LLM-free maths:
│   ├── vdot, workouts, planner, adaptation, validate   # plan construction + rules
│   ├── analytics.py          # legacy snapshot/aerobic/economy/race analysis
│   ├── durability.py         # running engine: CS/D', EF, decoupling, HRR, 80/20…
│   ├── load.py               # CTL/ATL/TSB, ACWR, HRV, sleep, readiness…
│   ├── strength.py           # HYROX stations, hybrid balance (needs benchmarks)
│   └── limiters.py           # ranks limiters → coach_input contract
├── garmin/client.py  # reads metrics + per-sample series, uploads workouts
└── hyrox/            # scraper.py (results.hyrox.com), analyzer.py (vs field benchmarks)
web/index.html        # the GitHub Pages dashboard (reads committed data/*.json)
scripts/build_site_data.py  # precomputes analytics/fitness/hyrox_analysis.json for the web (CI)
data/                 # profile.json, plan.json, activities.json, history.jsonl,
                      # details/{id}.json (splits + time-series), analyses/{id}.md +
                      # analyses/hyrox-{id}.md, hyrox.json, benchmarks.json, events.json
```

## HYROX + events flow (serverless writes)
The browser dispatches a GitHub Action with the user's PAT → the Action runs a CLI command
that writes `data/*.json` + commits → `pages.yml` (which reacts to those workflows in its
`workflow_run` list) rebuilds and redeploys. Mirror this for any new browser-driven write:
- `hyrox.yml` → `paceforge hyrox-search|hyrox-import` → `data/hyrox_preview.json` (pick-list
  the UI polls on raw.githubusercontent.com) then `data/hyrox.json`.
- `save-events.yml` → `data/events.json`.
- `build_site_data.py` derives `data/hyrox_analysis.json` (`{races, priorities, progression}`)
  from `hyrox.json` at deploy time.

## The AI / validation split
Deterministic facts (paces, plan structure) stay in code. Claude **proposes** a plan
(scaffold with `paceforge plan`, then personalise), `engine/validate.py` **checks** it.
Never invent paces — the engine derives them.

## Commands
```bash
.venv/bin/ruff check src/ tests/    # lint (must pass before commit)
.venv/bin/pytest tests/ -q          # tests (must pass before push)
.venv/bin/paceforge sync|analyze|plan|validate|push|status|hyrox-search|hyrox-import
```

## Conventions
- Python 3.11+, ruff 100-char lines, `from __future__ import annotations` at top.
- One behaviour module (`actions.py`) — keep CLI/MCP as thin wrappers, no duplicated logic.
- Commit messages: `area: short description`. Run ruff + pytest before committing.
