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
