"""PaceForge stdio MCP server — exposes the same actions to the Claude desktop app.

Thin wrappers over :mod:`paceforge.actions` and :mod:`paceforge.store`; no logic
lives here. Run with ``paceforge-mcp`` (stdio transport).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from paceforge import actions, store

mcp = FastMCP("paceforge")


@mcp.tool()
def garmin_sync(lookback_days: int = 90) -> dict:
    """Pull Garmin metrics + activities into the data store and return a summary."""
    return actions.sync(lookback_days=lookback_days)


@mcp.tool()
def get_profile() -> dict | None:
    """Return the stored fitness profile (VO2max, HRV, readiness, recent activities)."""
    p = store.load_profile()
    return p.model_dump(mode="json") if p else None


@mcp.tool()
def get_plan() -> dict | None:
    """Return the current training plan from data/plan.json."""
    p = store.load_plan()
    return p.model_dump(mode="json") if p else None


@mcp.tool()
def scaffold_plan(goal: dict) -> dict:
    """Build a deterministic baseline plan from the stored profile and save it.

    ``goal`` matches TrainingGoal: goal_type (5K/10K/HALF_MARATHON/MARATHON/HYROX),
    target_date (YYYY-MM-DD), experience_level, training_days, long_run_day.
    Personalise the saved plan.json on top, then call validate_plan.
    """
    return actions.scaffold(goal)


@mcp.tool()
def analyze() -> dict:
    """Run the full analytics engine (aerobic, economy, load/recovery, predictions)."""
    return actions.analyze()


@mcp.tool()
def validate_plan() -> list[str]:
    """Validate data/plan.json against the rules. Empty list means valid."""
    return actions.validate()


@mcp.tool()
def garmin_push_workout(week: int | None = None, dry_run: bool = False) -> dict:
    """Push one plan week's workouts to Garmin (validates first). Use dry_run to preview."""
    return actions.push(week=week, dry_run=dry_run)


@mcp.tool()
def strava_recent(limit: int = 10) -> list[dict]:
    """List recent Strava activities."""
    return actions.strava_recent(limit=limit)


@mcp.tool()
def strava_push(activity_id: int, description: str) -> dict:
    """Set a Strava activity's description (e.g. push Claude's workout analysis)."""
    return actions.strava_update_description(activity_id, description)


@mcp.tool()
def hyrox_analyze(race: dict) -> dict:
    """Analyze a HYROX race result (running fade, station breakdown vs field benchmarks).

    ``race`` matches the HyroxRaceResult schema: total_time_seconds and a list of
    splits ``[{"name": "Running_1", "time_seconds": 230}, ...]``.
    """
    from paceforge.hyrox.analyzer import analyze_race
    from paceforge.hyrox.models import HyroxRaceResult

    return analyze_race(HyroxRaceResult.model_validate(race))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
