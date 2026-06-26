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
    store.append_daily_history(profile)
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
        "matched_workouts": matched,
    }


def _match_plan() -> int:
    """Re-match stored activities to the active plan's workouts. Returns matched count."""
    from paceforge.engine.matching import match_plan_to_activities

    plan = store.load_plan()
    if not plan:
        return 0
    changed = match_plan_to_activities(plan, store.load_activities())
    if changed:
        store.save_plan(plan)
    return changed


def _extract_series(metrics: dict, max_points: int = 120) -> list | None:
    """Downsample Garmin's per-sample metrics into a compact [{t, hr, pace}] series.

    Reads metricDescriptors/activityDetailMetrics; keeps elapsed time, heart rate and
    pace (from speed). Returns None when there's no HR or speed channel (so cardio with
    only HR still yields an HR line, and a run yields both).
    """
    if not isinstance(metrics, dict):
        return None
    descs = metrics.get("metricDescriptors") or []
    rows = metrics.get("activityDetailMetrics") or []
    if not descs or not rows:
        return None
    idx = {d.get("key"): d.get("metricsIndex") for d in descs if isinstance(d, dict)}
    hr_i, sp_i, t_i = (idx.get("directHeartRate"), idx.get("directSpeed"),
                       idx.get("sumElapsedDuration"))
    # Cadence (steps/min, both feet) + stride length — the running-economy channels.
    cad_i = idx.get("directDoubleCadence")
    cad_single = idx.get("directRunCadence") if cad_i is None else None
    str_i = idx.get("directStrideLength")
    if hr_i is None and sp_i is None:
        return None
    step = max(1, -(-len(rows) // max_points))  # ceil division → never exceed max_points
    series = []
    for row in rows[::step]:
        m = row.get("metrics") if isinstance(row, dict) else None
        if not isinstance(m, list):
            continue
        def at(i, m=m):
            return m[i] if (i is not None and i < len(m)) else None
        hr, sp, t = at(hr_i), at(sp_i), at(t_i)
        cad = at(cad_i)
        if cad is None and cad_single is not None:  # single-foot cadence → double it
            sc = at(cad_single)
            cad = sc * 2 if sc is not None else None
        stride = at(str_i)  # metres (Garmin) — normalize to cm in the UI
        # speed (m/s) → pace (s/km); ignore near-standstill so pace doesn't blow up.
        pace = round(1000 / sp, 1) if sp and sp > 0.3 else None
        series.append({
            "t": round(t) if t is not None else None,
            "hr": round(hr) if hr is not None else None,
            "pace": pace,
            "cad": round(cad) if cad else None,
            "stride": round(stride, 2) if stride else None,
        })
    return series or None


# Bump when _trim_detail's shape changes so sync re-fetches older stored details.
_DETAIL_VERSION = 3  # v3 adds cadence + stride-length to the time-series


def _trim_detail(detail: dict) -> dict:
    """Reduce a raw ``get_activity_detail`` blob to the lean shape the web charts use."""
    out: dict = {"activity_id": detail.get("activity_id"), "v": _DETAIL_VERSION}

    series = _extract_series(detail.get("metrics"))
    if series:
        out["series"] = series

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
        if aid is None or aid in seen:
            continue
        seen.add(aid)
        # Skip only if the stored detail is already at the current schema version;
        # older details get re-fetched once so the new charts get their time-series.
        if store.has_detail(aid) and (store.load_detail(aid) or {}).get("v", 0) >= _DETAIL_VERSION:
            continue
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


def fitness() -> dict:
    """Fitness 2.0 assessment: running-engine/durability, load/recovery/wellbeing,
    strength/HYROX, and the readiness-gated ranked limiters + LLM-coach contract."""
    from paceforge.engine.durability import compute_running_metrics
    from paceforge.engine.limiters import rank_limiters
    from paceforge.engine.load import compute_load_recovery
    from paceforge.engine.strength import compute_strength_hyrox

    profile = store.load_profile()
    if profile is None:
        raise RuntimeError("No profile — run `paceforge sync` first.")
    activities = store.load_activities()
    details = store.load_all_details()
    running = compute_running_metrics(activities, details, profile)
    load = compute_load_recovery(store.load_history(), activities, profile)
    strength = compute_strength_hyrox(
        store.load_hyrox_results(), store.load_benchmarks(), profile, activities, details)
    limiters = rank_limiters(running, load, strength)
    return {"running": running, "load": load, "strength": strength, **limiters}


# ── HYROX race import (results.hyrox.com) ────────────────────────────


def hyrox_search(name: str, *, gender: str = "M", firstname: str = "") -> dict:
    """Search results.hyrox.com for an athlete; write data/hyrox_preview.json.

    Returns a pick-list (no split fetches) the web UI renders so the athlete can
    confirm which races are actually theirs before importing.
    """
    from datetime import datetime

    from paceforge.hyrox.scraper import HyroxScraper

    scraper = HyroxScraper()
    try:
        summaries = scraper.search_preview(name, firstname=firstname, gender=gender)
    finally:
        scraper.close()

    preview = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "query": {"name": name, "gender": gender, "firstname": firstname},
        "results": [
            {
                "name": s.get("name", ""),
                "city": s.get("city", ""),
                "event_date": s.get("city_raw", "") or s.get("city", ""),
                "total_time": s.get("total_time", ""),
                "rank": s.get("rank", ""),
                "athlete_url": s.get("athlete_url", ""),
            }
            for s in summaries
        ],
    }
    store.save_hyrox_preview(preview)
    return preview


def hyrox_import(
    name: str,
    *,
    gender: str = "M",
    firstname: str = "",
    selected_urls: list[str] | None = None,
) -> dict:
    """Fetch full race splits for the chosen athlete URLs; write data/hyrox.json."""
    from paceforge.hyrox.scraper import HyroxScraper, to_cached_dict

    scraper = HyroxScraper()
    try:
        results = scraper.search_athlete(
            name, firstname=firstname, gender=gender, selected_urls=selected_urls
        )
    finally:
        scraper.close()

    store.save_hyrox_results(
        to_cached_dict(results, search_name=name, search_gender=gender)
    )
    return {"imported": len(results), "races": [r.city or r.event_date for r in results]}


def hyrox_import_profile(slug: str, *, gender: str = "M") -> dict:
    """Import every race for a hyresult.com athlete profile → data/hyrox.json.

    hyresult.com is the source of truth: results.hyrox.com's season-overall
    ranking drops races (e.g. Berlin 2026) and reports season-cumulative ranks,
    whereas hyresult has every race with correct per-race Overall + Age-group
    ranks and full splits.
    """
    from paceforge.hyrox.hyresult import HyresultScraper

    scraper = HyresultScraper()
    try:
        results = scraper.fetch_athlete(slug)
    finally:
        scraper.close()

    store.save_hyrox_results({
        "search_name": slug,
        "search_gender": gender,
        "results": [r.model_dump(mode="json") for r in results],
    })
    return {"imported": len(results), "races": [r.city or r.event_date for r in results]}


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
