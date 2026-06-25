"""Tests for the per-activity splits pipeline (store + sync_details + trim)."""

import pytest

from paceforge import actions, store
from paceforge.models.profile import RecentActivity


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)


def _activity(activity_id: int) -> RecentActivity:
    return RecentActivity(
        activity_id=activity_id,
        name="run",
        activity_type="running",
        start_time=f"2026-06-{10 + activity_id:02d}T07:00:00",
        distance_meters=10000,
        duration_seconds=3000,
    )


class FakeClient:
    def __init__(self):
        self.calls = []

    def get_activity_detail(self, activity_id):
        self.calls.append(activity_id)
        return {
            "activity_id": activity_id,
            "splits": {"lapDTOs": [
                {"distance": 1000, "duration": 300, "averageHR": 150, "maxHR": 160},
                {"distance": 1000, "duration": 290, "averageHR": 155, "maxHR": 162},
            ]},
        }


class TestTrimDetail:
    def test_per_lap_pace_is_seconds_per_km(self):
        out = actions._trim_detail({"activity_id": 7, "splits": {"lapDTOs": [
            {"distance": 1000, "duration": 300, "averageHR": 150}]}})
        assert out["splits"][0]["pace_sec"] == 300.0

    def test_keeps_lap_heart_rate(self):
        out = actions._trim_detail({"activity_id": 7, "splits": {"lapDTOs": [
            {"distance": 1000, "duration": 300, "averageHR": 150}]}})
        assert out["splits"][0]["avg_hr"] == 150


class TestStoreDetail:
    def test_save_then_load_roundtrips(self):
        store.save_detail(42, {"activity_id": 42, "splits": []})
        assert store.load_detail(42)["activity_id"] == 42

    def test_has_detail_false_when_absent(self):
        assert store.has_detail(999) is False


class TestSyncDetails:
    def test_fetches_each_recent_activity_once(self):
        store.save_activities([_activity(1), _activity(2)])
        n = actions._sync_details(FakeClient(), limit=40)
        assert n == 2
        assert store.has_detail(1) and store.has_detail(2)

    def test_skips_activities_already_stored(self):
        store.save_activities([_activity(1), _activity(2)])
        client = FakeClient()
        actions._sync_details(client, limit=40)
        client.calls.clear()
        again = actions._sync_details(client, limit=40)
        assert again == 0
        assert client.calls == []
