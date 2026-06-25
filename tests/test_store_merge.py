"""Tests for the merge-on-save behaviour in :mod:`paceforge.store`.

A Garmin sync only sees a recent window and intermittently returns null metrics;
saving must not let that erase good stored data.
"""

import pytest

from paceforge import store
from paceforge.models.profile import RecentActivity, UserFitnessProfile


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)


def _activity(activity_id: int, start_time: str) -> RecentActivity:
    return RecentActivity(
        activity_id=activity_id,
        name="run",
        activity_type="running",
        start_time=start_time,
        distance_meters=10000,
        duration_seconds=3000,
    )


class TestSaveProfileMerge:
    def test_null_vo2_does_not_overwrite_stored_value(self):
        store.save_profile(UserFitnessProfile(vo2_max=55.2))
        store.save_profile(UserFitnessProfile(vo2_max=None))
        assert store.load_profile().vo2_max == 55.2

    def test_fresh_value_replaces_stored_value(self):
        store.save_profile(UserFitnessProfile(vo2_max=55.2))
        store.save_profile(UserFitnessProfile(vo2_max=56.0))
        assert store.load_profile().vo2_max == 56.0


class TestSaveActivitiesMerge:
    def test_history_is_not_truncated_to_the_new_window(self):
        store.save_activities([_activity(1, "2026-01-01T07:00:00")])
        store.save_activities([_activity(2, "2026-06-01T07:00:00")])
        assert {a.activity_id for a in store.load_activities()} == {1, 2}

    def test_newest_activity_is_first(self):
        store.save_activities([_activity(1, "2026-01-01T07:00:00")])
        store.save_activities([_activity(2, "2026-06-01T07:00:00")])
        assert store.load_activities()[0].activity_id == 2
