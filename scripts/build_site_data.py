"""Precompute the derived JSON the static web UI reads.

The site is static (GitHub Pages), so anything the old FastAPI backend computed on
request must be baked into files at build time:

    data/analytics.json       — engine analytics over the stored profile
    data/hyrox_analysis.json  — per-race HYROX breakdown vs field benchmarks

Run from the repo root (CI does this in the Pages workflow before deploying):

    python scripts/build_site_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

from paceforge import actions
from paceforge.hyrox.analyzer import analyze_race
from paceforge.hyrox.models import HyroxRaceResult

DATA = Path("data")


def _write(name: str, payload: object) -> None:
    (DATA / name).write_text(json.dumps(payload, indent=2, default=str))
    print(f"  wrote data/{name}")


def main() -> int:
    _write("analytics.json", actions.analyze())

    hyrox = json.loads((DATA / "hyrox.json").read_text())
    analyses = [
        analyze_race(HyroxRaceResult.model_validate(r))
        for r in hyrox.get("results", [])
    ]
    _write("hyrox_analysis.json", analyses)

    # Placeholder so the UI's weekly view fetch never 404s. Claude writes a real
    # one (with a populated `content`) into data/weekly.json when reviewing a week.
    if not (DATA / "weekly.json").exists():
        _write("weekly.json", {"content": None})

    print(f"done — {len(analyses)} hyrox races analysed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
