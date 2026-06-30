# PaceForge

A personal, serverless running coach for Garmin. Pulls your Garmin Connect fitness
data, builds and adapts training plans, pushes structured workouts to your watch,
and reviews your training — with **no backend, no database, and no LLM API bill**.

It runs four ways, all free beyond a Claude subscription:
- a **web dashboard** on GitHub Pages — **[vperrod.github.io/paceforge](https://vperrod.github.io/paceforge/)** (single-user, static, reads the committed `data/*.json`),
- **Claude Code** in this repo (run the CLI directly),
- the **Claude desktop app** via a local MCP server,
- **GitHub Actions** — a daily Garmin sync, an auto-analysis of completed workouts, and a weekly auto-review.

## How it works

- **Deterministic maths in code**: VDOT→pace zones, workout construction, the template
  planner, and plan validation live in the `paceforge` package.
- **Judgement is Claude's**: plan design, adaptation to your current state, activity
  analysis, and weekly reviews — guided by the coach skill (`.claude/skills/coach/`).
- **State is files**: everything lives in git-tracked `data/*.json`. Git is the history.

Claude **proposes** a plan; the engine **validates** it (paces ordered, no back-to-back
intense days, sane volume ramps) before anything reaches your watch.

## Web dashboard

A desktop-first static dashboard ([vperrod.github.io/paceforge](https://vperrod.github.io/paceforge/)),
deployed by `pages.yml` and re-deployed automatically after each sync:

- **Overview** — recent activities, this week's plan, key stats.
- **Calendar** — compact month grid (weeks start Monday), with dots colour-coded by
  session type (easy, long, tempo, fast, cross-training); click a day to see the session
  inline (no popups); past days show what you actually did, upcoming days show the plan.
- **Activity detail** — opens as a page with **pace / heart-rate / cadence / stride-length**
  charts over time (with an efficient-range band on cadence & stride), an HR-zone
  distribution (with the bpm range per zone), a pace histogram, per-km splits,
  planned-vs-actual, and a Claude-written coaching analysis (with live progress while
  it's generated).
- **HYROX** — import every race from your hyresult.com athlete profile (`paceforge
  hyrox-import-profile <slug>`), then open each race for a full breakdown: per-race
  Overall and Age-group placing, a **field-percentile bar per segment**, a **station
  strengths radar**, a **pacing view** (run-lap fade + cumulative curve), a **roxzone
  transition spotlight**, a **vs-your-other-races** comparison, time split running vs
  stations vs roxzone, every split vs the field & top-3 average, a deterministic coach
  read (weaknesses, pacing mistakes, strengths), an optional Claude-written race review,
  and a cross-race **progression** view (finish-time trend, per-station evolution, and
  your biggest gaps to fix next).
- **Events** — add upcoming races/runs (Settings → Upcoming events); they show as a
  countdown on Overview and on the Calendar, and the coach rebalances your plan around
  them (taper into races, build between them) gated by your health metrics.
- **Fitness** — the full assessment (below).
- Edit the plan, trigger a Sync / Push-to-Garmin, or request a coach analysis straight
  from the browser via a GitHub fine-grained token (stored only in your browser).

## What it measures — Fitness 2.0

Deterministic engines (`paceforge/engine/`) compute a complete athlete assessment from the
Garmin time-series, then a **limiter-ranking** engine turns it into prioritised, readiness-gated
guidance the coach writes up. The Fitness page leads with **Coach's Take** — your top-3 limiters,
each with the metric evidence and a concrete "this week" action.

- **Engine** (`engine/durability.py`): Critical Speed / D′ (+ Critical Power / W′), efficiency-factor
  trend, vVO2max, aerobic decoupling, compromised-run fade, HR-recovery, 80/20 intensity distribution,
  pacing, economy-vs-pace.
- **Load & recovery** (`engine/load.py`): TRIMP load, CTL/ATL/TSB (fitness-fatigue-form), ACWR,
  monotony/strain, injury-spike guardrail, HRV baseline/CV, sleep debt/architecture, an overtraining
  early-warning composite, and a daily readiness score — alongside Garmin's native status.
- **Strength / HYROX** (`engine/strength.py`): station percentiles vs the field, in-race run fade,
  hybrid (run-vs-strength) balance — unlocked by a few one-time benchmarks entered on the Strength tab.

Activity-derived metrics work from existing data immediately; wellness trends fill in over ~6 weeks as
`data/history.jsonl` accumulates a daily snapshot.

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/paceforge login        # one-time Garmin auth (handles MFA) → prints GARMIN_TOKEN
```

Run `login` in a **real interactive terminal** — it prompts for your password (hidden) and
an MFA code, so it can't run in a non-interactive shell (a piped CI step or an agent's
`!`-prefixed shell fails with `EOFError`/`No valid Garmin token`).

To enable headless sync, set these GitHub Actions secrets:

| Secret | Purpose |
|--------|---------|
| `PACEFORGE_GARMIN_EMAIL` | Garmin login email |
| `GARMIN_TOKEN` | base64 token printed by `paceforge login` |
| `ACTIONS_PAT` | *(recommended)* fine-grained PAT — repo `paceforge`, **Secrets: Read & Write** |

```bash
.venv/bin/paceforge login | gh secret set GARMIN_TOKEN --repo <owner>/paceforge   # one line
```

**Token self-refresh:** Garmin's OAuth2 token is short-lived, so a stored `GARMIN_TOKEN`
goes stale within days and the daily sync starts failing with `No valid Garmin token`. With
`ACTIONS_PAT` set, `sync.yml` writes the freshly-refreshed token back into the `GARMIN_TOKEN`
secret after every run, so it never expires unattended. Without `ACTIONS_PAT` the refresh
step is skipped cleanly and you must re-set `GARMIN_TOKEN` by hand. The underlying OAuth1
token still expires roughly yearly — when it does, run `paceforge login` again.

See `.env.example` for all variables.

## Usage

```bash
paceforge sync                              # Garmin metrics + activities → data/*.json
paceforge analyze                           # aerobic/economy/load/predictions analysis
paceforge plan --goal MARATHON --date 2026-10-04 --level intermediate
paceforge validate                          # check data/plan.json against the rules
paceforge push --dry-run                    # preview the week's workouts
paceforge push                              # upload to Garmin
paceforge hyrox-import-profile <slug>       # import all races from a hyresult.com profile
paceforge hyrox-search "Surname" --gender M # (legacy) results.hyrox.com name search
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
