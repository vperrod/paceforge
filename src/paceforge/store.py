"""File-based state — ``data/*.json`` is the database (single user, git-tracked).

No DB, no ORM. Each domain object is a Pydantic model serialized to JSON. Git is
the history and backup. Override the location with ``PACEFORGE_DATA_DIR``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from paceforge.models.plan import TrainingPlan
from paceforge.models.profile import RecentActivity, UserFitnessProfile

DATA_DIR = Path(os.getenv("PACEFORGE_DATA_DIR", "data"))


def _path(name: str) -> Path:
    return DATA_DIR / name


def _write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)


def load_profile() -> UserFitnessProfile | None:
    p = _path("profile.json")
    return UserFitnessProfile.model_validate_json(p.read_text()) if p.exists() else None


_EMPTY = (None, [], {}, "")


def save_profile(profile: UserFitnessProfile) -> None:
    """Persist the profile, preserving prior non-empty fields the fresh fetch dropped.

    Garmin's wellness endpoints intermittently return null for VO2max/HRV/readiness
    for a given day. Without this merge a sync would overwrite good values with null,
    so we only let a new value replace an existing one when the new value is non-empty.
    """
    existing = load_profile()
    if existing is not None:
        merged = profile.model_dump()
        old = existing.model_dump()
        for field, value in merged.items():
            if value in _EMPTY and old.get(field) not in _EMPTY:
                merged[field] = old[field]
        profile = UserFitnessProfile.model_validate(merged)
    _write(_path("profile.json"), profile.model_dump_json(indent=2))


# Slim daily-wellness fields persisted to history.jsonl for trend metrics
# (CTL/ATL/TSB, HRV baseline, sleep debt) — profile.json only ever holds "today".
_HISTORY_FIELDS = (
    "vo2_max", "resting_hr", "max_hr", "hrv_status", "hrv_last_night",
    "training_readiness", "training_status", "training_load_7day", "load_focus",
    "body_battery_current", "body_battery_high", "body_battery_low",
    "sleep_score", "sleep_duration_seconds", "sleep_deep_seconds",
    "sleep_rem_seconds", "sleep_light_seconds", "stress_avg", "stress_high",
    "weekly_mileage_km",
)


def append_daily_history(profile: UserFitnessProfile) -> None:
    """Append one slim wellness snapshot for the profile's date to history.jsonl.

    Upserts by date (a re-sync the same day overwrites that day's row). Trend
    metrics need this daily series — every day not stored is permanently lost.
    """
    p = profile.model_dump()
    date = p.get("profile_date")
    if not date:
        return
    date = str(date)
    row = {"date": date, **{f: p.get(f) for f in _HISTORY_FIELDS}}
    rows = [r for r in load_history() if r.get("date") != date]
    rows.append(row)
    rows.sort(key=lambda r: r.get("date") or "")
    _write(_path("history.jsonl"),
           "\n".join(json.dumps(r, default=str) for r in rows) + "\n")


def load_history() -> list[dict]:
    """All stored daily wellness snapshots, oldest first."""
    p = _path("history.jsonl")
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def load_plan() -> TrainingPlan | None:
    p = _path("plan.json")
    return TrainingPlan.model_validate_json(p.read_text()) if p.exists() else None


def save_plan(plan: TrainingPlan) -> None:
    _write(_path("plan.json"), plan.model_dump_json(indent=2))


def load_activities() -> list[RecentActivity]:
    p = _path("activities.json")
    if not p.exists():
        return []
    return [RecentActivity.model_validate(a) for a in json.loads(p.read_text())]


def save_activities(activities: list[RecentActivity]) -> None:
    """Merge a fresh activity window into the stored history (union by activity_id).

    A sync only sees a recent lookback window; replacing the file would cap history
    at that window. We union with what's already stored, letting the fresh copy win
    for any overlapping id, and keep the newest first.
    """
    by_id = {a.activity_id: a for a in load_activities()}
    for a in activities:
        by_id[a.activity_id] = a
    merged = sorted(by_id.values(), key=lambda a: str(a.start_time or ""), reverse=True)
    payload = json.dumps([a.model_dump(mode="json") for a in merged], indent=2)
    _write(_path("activities.json"), payload)


# ── Per-activity detail (splits/HR/weather for the web charts) ────────


def _detail_path(activity_id: int | str) -> Path:
    return _path("details") / f"{activity_id}.json"


def has_detail(activity_id: int | str) -> bool:
    return _detail_path(activity_id).exists()


def load_detail(activity_id: int | str) -> dict | None:
    p = _detail_path(activity_id)
    return json.loads(p.read_text()) if p.exists() else None


def save_detail(activity_id: int | str, detail: dict) -> None:
    _write(_detail_path(activity_id), json.dumps(detail, indent=2, default=str))
