"""Tests for the HYROX import path: scraper helper, actions write-path, events store."""

from __future__ import annotations

import json

import pytest

from paceforge import actions, store
from paceforge.hyrox import scraper as scraper_mod
from paceforge.hyrox.models import HyroxRaceResult, HyroxSplit
from paceforge.hyrox.scraper import to_cached_dict


@pytest.fixture(autouse=True)
def _tmp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)


def _race(city: str, secs: float) -> HyroxRaceResult:
    return HyroxRaceResult(
        name="Perez Rodriguez, Victor",
        city=city,
        event_date=city,
        total_time_seconds=secs,
        total_time_display="1:03:46",
        splits=[HyroxSplit(name="Running_1", time_seconds=280.0)],
        athlete_url=f"?idp={city}",
    )


def test_to_cached_dict_shape_round_trips_through_store():
    cached = to_cached_dict([_race("Dublin 2025", 3826)], search_name="Perez", search_gender="M")
    assert cached["search_name"] == "Perez"
    assert cached["search_gender"] == "M"
    store.save_hyrox_results(cached)
    loaded = store.load_hyrox_results()
    assert len(loaded) == 1
    assert loaded[0]["splits"][0]["time_seconds"] == 280.0


class _FakeScraper:
    """Stand-in for HyroxScraper — no network."""

    closed = False

    def search_preview(self, name, *, firstname="", gender="M"):
        return [{"name": name, "city": "Dublin", "city_raw": "Dublin 2025",
                 "total_time": "1:03:46", "rank": "5", "athlete_url": "?idp=dub"}]

    def search_athlete(self, name, *, firstname="", gender="M", selected_urls=None):
        # Honour the user's pick-list.
        assert selected_urls == ["?idp=dub"]
        return [_race("Dublin 2025", 3826)]

    def close(self):
        type(self).closed = True


def test_hyrox_search_writes_preview(monkeypatch):
    monkeypatch.setattr(scraper_mod, "HyroxScraper", _FakeScraper)
    preview = actions.hyrox_search("Perez", gender="M")
    assert preview["results"][0]["athlete_url"] == "?idp=dub"
    assert "generated_at" in preview
    on_disk = json.loads((store.DATA_DIR / "hyrox_preview.json").read_text())
    assert on_disk["results"][0]["event_date"] == "Dublin 2025"


def test_hyrox_import_writes_results(monkeypatch):
    monkeypatch.setattr(scraper_mod, "HyroxScraper", _FakeScraper)
    summary = actions.hyrox_import("Perez", gender="M", selected_urls=["?idp=dub"])
    assert summary["imported"] == 1
    assert store.load_hyrox_results()[0]["city"] == "Dublin 2025"


def test_events_round_trip():
    assert store.load_events() == []
    events = [{"date": "2026-11-15", "name": "HYROX Valencia", "type": "HYROX", "goal_time": "1:02:00"}]
    store.save_events(events)
    assert store.load_events() == events


def test_parse_listing_extracts_athlete():
    html = """
    <li class="list-group-item">
      <div class="type-place">5</div>
      <h4 class="type-fullname"><a href="?content=detail&idp=ABC">Perez Rodriguez, Victor</a></h4>
      <div class="type-field">City Dublin 2025</div>
      <div class="pull-right"><div class="type-time">Total 1:03:46</div></div>
    </li>
    """
    rows = scraper_mod.HyroxScraper._parse_listing(object.__new__(scraper_mod.HyroxScraper), html)
    assert len(rows) == 1
    assert rows[0]["name"] == "Perez Rodriguez, Victor"
    assert rows[0]["athlete_url"] == "?content=detail&idp=ABC"
    assert rows[0]["city"] == "Dublin"
    assert rows[0]["total_time"] == "1:03:46"
