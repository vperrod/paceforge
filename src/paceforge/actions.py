"""Core actions shared by the CLI and the MCP server.

One module, two entrypoints — ``cli.py`` and ``mcp_server.py`` are thin wrappers
over these functions. All state lives in ``data/*.json`` via :mod:`paceforge.store`.

Garmin auth: a one-time interactive ``login()`` dumps a ~1-year token to
``PACEFORGE_GARMIN_TOKEN_DIR`` and returns a base64 blob to store as the
``GARMIN_TOKEN`` secret. Headless runs (CI) rematerialize that blob and reconnect
with no password and no MFA.
"""

from __future__ import annotations

import base64
import getpass
import io
import logging
import os
import tarfile
from datetime import date
from pathlib import Path

from paceforge import store
from paceforge.engine.analytics import compute_all
from paceforge.engine.validate import validate_plan
from paceforge.garmin.client import GarminClient
from paceforge.models.plan import TrainingPlan, TrainingWeek

logger = logging.getLogger(__name__)

# ── Garmin auth ──────────────────────────────────────────────────────


def _token_dir() -> Path:
    return Path(os.getenv("PACEFORGE_GARMIN_TOKEN_DIR", "~/.garminconnect")).expanduser()


def _has_token(token_dir: Path) -> bool:
    return token_dir.exists() and any(token_dir.iterdir())


def _materialize_token(token_dir: Path) -> None:
    """Unpack the GARMIN_TOKEN secret into the token dir for headless runs."""
    blob = os.getenv("GARMIN_TOKEN")
    if not blob or _has_token(token_dir):
        return
    token_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(blob)), mode="r:gz") as tar:
        tar.extractall(token_dir)  # noqa: S202 — our own token archive


def _export_token(token_dir: Path) -> str:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in sorted(token_dir.iterdir()):
            if f.is_file():
                tar.add(f, arcname=f.name)
    return base64.b64encode(buf.getvalue()).decode()


def garmin_connect() -> GarminClient:
    email = os.environ["PACEFORGE_GARMIN_EMAIL"]
    token_dir = _token_dir()
    _materialize_token(token_dir)
    client = GarminClient.try_reconnect(email, str(token_dir))
    if client is None:
        raise RuntimeError("No valid Garmin token — run `paceforge login` once to create one.")
    return client


def login() -> str:
    """Interactive first-time login (handles MFA). Returns the GARMIN_TOKEN blob."""
    email = os.environ.get("PACEFORGE_GARMIN_EMAIL") or input("Garmin email: ")
    password = os.environ.get("PACEFORGE_GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")
    token_dir = _token_dir()
    token_dir.mkdir(parents=True, exist_ok=True)
    client = GarminClient(email, password, token_dir=str(token_dir))
    if client.login() == "mfa_required":
        client.complete_mfa(input("MFA code: ").strip())
    return _export_token(token_dir)


# ── Sync / analyse / push ────────────────────────────────────────────


def sync(lookback_days: int = 90, details_limit: int = 40) -> dict:
    """Pull metrics + activities from Garmin into data/*.json (+ recent splits)."""
    client = garmin_connect()
    profile = client.get_fitness_profile(lookback_days=lookback_days)
    store.save_profile(profile)
    store.save_activities(profile.recent_activities)
    new_details = _sync_details(client, limit=details_limit)
    matched = _match_plan()
    return {
        "vo2_max": profile.vo2_max,
        "training_readiness": profile.training_readiness,
        "hrv_status": profile.hrv_status,
        "training_status": profile.training_status,
        "activities": len(profile.recent_activities),
        "new_details": new_details,
        "newly_matched": matched,
    }


def _match_plan() -> int:
    """Re-match stored activities to the active plan's workouts. Returns count changed."""
    from paceforge.engine.matching import match_plan_to_activities

    plan = store.load_plan()
    if not plan:
        return 0
    changed = match_plan_to_activities(plan, store.load_activities())
    if changed:
        store.save_plan(plan)
    return changed


def _trim_detail(detail: dict) -> dict:
    """Reduce a raw ``get_activity_detail`` blob to the lean shape the web charts use."""
    out: dict = {"activity_id": detail.get("activity_id")}

    splits = detail.get("splits") or {}
    laps = splits.get("lapDTOs") if isinstance(splits, dict) else (
        splits if isinstance(splits, list) else [])
    segs = []
    for i, lap in enumerate(laps or [], start=1):
        if not isinstance(lap, dict):
            continue
        dist = lap.get("distance") or 0
        dur = lap.get("duration") or lap.get("movingDuration") or 0
        segs.append({
            "n": i,
            "distance_m": round(dist, 1) if dist else None,
            "duration_s": round(dur, 1) if dur else None,
            "pace_sec": round(dur / (dist / 1000), 1) if dist and dur else None,
            "avg_hr": lap.get("averageHR"),
            "max_hr": lap.get("maxHR"),
            "elev_gain": lap.get("elevationGain"),
            "avg_cadence": (lap.get("averageRunCadence")
                            or lap.get("averageRunningCadenceInStepsPerMinute")),
        })
    out["splits"] = segs

    hz = detail.get("hr_zones")
    if isinstance(hz, list):
        out["hr_zones"] = [
            {"zone": z.get("zoneNumber"), "secs": z.get("secsInZone")}
            for z in hz if isinstance(z, dict)
        ]

    w = detail.get("weather")
    if isinstance(w, dict) and w:
        wt = w.get("weatherTypeDTO") if isinstance(w.get("weatherTypeDTO"), dict) else {}
        out["weather"] = {
            "temp_c": w.get("temp"),
            "feels_c": w.get("apparentTemp"),
            "humidity": w.get("relativeHumidity"),
            "desc": wt.get("desc"),
        }
    return out


def _sync_details(client: GarminClient, limit: int = 40) -> int:
    """Fetch + store per-activity splits for the recent ``limit`` activities plus any
    matched by the current plan. Incremental (skips stored ids); best-effort per
    activity so one bad fetch never fails the whole sync. Returns count newly stored.
    """
    ids: list = [a.activity_id for a in store.load_activities()[:limit]]
    plan = store.load_plan()
    if plan is not None:
        for wk in plan.weeks:
            for wo in wk.workouts:
                ids.extend(wo.matched_activity_ids or [])

    seen: set = set()
    fetched = 0
    for aid in ids:
        if aid is None or aid in seen or store.has_detail(aid):
            continue
        seen.add(aid)
        try:
            store.save_detail(aid, _trim_detail(client.get_activity_detail(aid)))
            fetched += 1
        except Exception:
            logger.warning("activity detail fetch failed for %s", aid, exc_info=True)
    return fetched


def scaffold(goal: dict) -> dict:
    """Build a deterministic baseline plan (correct paces + valid structure) and save it.

    The starting point for the coach loop: Claude personalises the saved plan.json
    on top of this, then re-validates.
    """
    from paceforge.engine.planner import generate_plan
    from paceforge.models.profile import TrainingGoal

    profile = store.load_profile()
    if profile is None:
        raise RuntimeError("No profile — run `paceforge sync` first.")
    plan = generate_plan(profile, TrainingGoal.model_validate(goal))
    store.save_plan(plan)
    return {
        "name": plan.name,
        "weeks": plan.total_weeks,
        "vdot": plan.vdot,
        "pace_source": plan.pace_source,
        "issues": validate_plan(plan),
    }


def analyze() -> dict:
    """Run the full analytics engine over the stored profile."""
    profile = store.load_profile()
    if profile is None:
        raise RuntimeError("No profile — run `paceforge sync` first.")
    return compute_all(profile)


def validate() -> list[str]:
    plan = store.load_plan()
    if plan is None:
        raise RuntimeError("No plan at data/plan.json.")
    return validate_plan(plan)


def _select_week(plan: TrainingPlan, week: int | None) -> TrainingWeek:
    if week is not None:
        for wk in plan.weeks:
            if wk.week_number == week:
                return wk
        raise RuntimeError(f"Week {week} not in plan.")
    today = date.today()
    upcoming = [
        wk for wk in plan.weeks
        if any(w.scheduled_date and w.scheduled_date >= today for w in wk.workouts)
    ]
    return upcoming[0] if upcoming else plan.weeks[0]


def push(week: int | None = None, dry_run: bool = False) -> dict:
    """Push one plan week's workouts to Garmin (validates the plan first)."""
    plan = store.load_plan()
    if plan is None:
        raise RuntimeError("No plan at data/plan.json.")
    issues = validate_plan(plan)
    if issues:
        raise RuntimeError("Plan failed validation — fix before pushing:\n- " + "\n- ".join(issues))
    wk = _select_week(plan, week)
    workouts = [w for w in wk.workouts if w.workout_type.value != "rest"]
    summary = [
        {"name": w.name, "date": str(w.scheduled_date), "type": w.workout_type.value}
        for w in workouts
    ]
    if dry_run:
        return {"week": wk.week_number, "dry_run": True, "workouts": summary}
    paces = {
        "easy_pace": plan.easy_pace,
        "marathon_pace": plan.marathon_pace,
        "threshold_pace": plan.threshold_pace,
        "interval_pace": plan.interval_pace,
    }
    client = garmin_connect()
    results = client.push_plan_week(workouts, plan_paces=paces)
    return {"week": wk.week_number, "pushed": len(results), "workouts": summary}


def status() -> dict:
    profile = store.load_profile()
    plan = store.load_plan()
    return {
        "profile": None if not profile else {
            "vo2_max": profile.vo2_max,
            "training_readiness": profile.training_readiness,
            "hrv_status": profile.hrv_status,
            "activities": len(profile.recent_activities),
            "profile_date": str(profile.profile_date),
        },
        "plan": None if not plan else {
            "name": plan.name,
            "goal": plan.goal_type,
            "target_date": str(plan.target_date),
            "weeks": plan.total_weeks,
            "accepted": plan.accepted,
        },
    }
