"""Daily wellness history storage (the time-series trend metrics depend on)."""
import pytest

from paceforge import store
from paceforge.engine.analytics import _normalize_lt_speed
from paceforge.models.profile import UserFitnessProfile


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)


def _profile(date, **kw):
    return UserFitnessProfile(profile_date=date, **kw)


def test_append_then_load_roundtrip():
    store.append_daily_history(_profile("2026-06-01", vo2_max=55.0, resting_hr=46))
    rows = store.load_history()
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-06-01" and rows[0]["vo2_max"] == 55.0


def test_upsert_replaces_same_day():
    store.append_daily_history(_profile("2026-06-01", resting_hr=46))
    store.append_daily_history(_profile("2026-06-01", resting_hr=50))
    rows = store.load_history()
    assert len(rows) == 1 and rows[0]["resting_hr"] == 50


def test_keeps_distinct_days_sorted():
    store.append_daily_history(_profile("2026-06-03"))
    store.append_daily_history(_profile("2026-06-01"))
    store.append_daily_history(_profile("2026-06-02"))
    assert [r["date"] for r in store.load_history()] == ["2026-06-01", "2026-06-02", "2026-06-03"]


def test_load_empty_when_absent():
    assert store.load_history() == []


def test_no_date_is_ignored():
    store.append_daily_history(UserFitnessProfile.model_construct(profile_date=None))
    assert store.load_history() == []


def test_lt_speed_normalizes_the_tenths_bug():
    # Garmin returned 0.386 — really 3.86 m/s (4:19/km). The fix multiplies by 10.
    assert round(_normalize_lt_speed(0.38611003), 2) == 3.86
    assert _normalize_lt_speed(3.86) == 3.86  # already-normalized is idempotent
