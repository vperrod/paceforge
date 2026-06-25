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


def save_profile(profile: UserFitnessProfile) -> None:
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
    payload = json.dumps([a.model_dump(mode="json") for a in activities], indent=2)
    _write(_path("activities.json"), payload)
