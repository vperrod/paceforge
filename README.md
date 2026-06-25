# PaceForge

A personal, serverless running coach for Garmin. Pulls your Garmin Connect fitness
data, builds and adapts training plans, pushes structured workouts to your watch,
and reviews your training — with **no backend, no database, and no LLM API bill**.

It runs three ways, all free beyond a Claude subscription:
- **Claude Code** in this repo (run the CLI directly),
- the **Claude desktop app** via a local MCP server,
- **GitHub Actions** — a daily Garmin sync and a weekly auto-review.

## How it works

- **Deterministic maths in code**: VDOT→pace zones, workout construction, the template
  planner, and plan validation live in the `paceforge` package.
- **Judgement is Claude's**: plan design, adaptation to your current state, activity
  analysis, and weekly reviews — guided by the coach skill (`.claude/skills/coach/`).
- **State is files**: everything lives in git-tracked `data/*.json`. Git is the history.

Claude **proposes** a plan; the engine **validates** it (paces ordered, no back-to-back
intense days, sane volume ramps) before anything reaches your watch.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/paceforge login        # one-time Garmin auth (handles MFA) → prints GARMIN_TOKEN
```

Store the printed `GARMIN_TOKEN` (and `PACEFORGE_GARMIN_EMAIL`) as GitHub Actions
secrets to enable headless sync. See `.env.example` for all variables.

## Usage

```bash
paceforge sync                              # Garmin metrics + activities → data/*.json
paceforge analyze                           # aerobic/economy/load/predictions analysis
paceforge plan --goal MARATHON --date 2026-10-04 --level intermediate
paceforge validate                          # check data/plan.json against the rules
paceforge push --dry-run                    # preview the week's workouts
paceforge push                              # upload to Garmin
```

Or just ask Claude: *"sync and review my week"*, *"build my marathon block"*,
*"reschedule Thursday's tempo to Saturday"* — it drives the same commands.

## Migrating from the old hosted app

```bash
# Download paceforge.db from Azure (Kudu: /home/data/paceforge.db), then:
python scripts/migrate_from_sqlite.py paceforge.db --email you@example.com
paceforge status                            # confirm your plan + activities came across
```

Once verified, `scripts/decommission_azure.sh` tears down the old App Service + registry.

## Tests

```bash
.venv/bin/pytest tests/ -q
```

## License

MIT
