"""One-time migration: pull your data out of the old PaceForge SQLite DB into data/*.json.

Get the DB off Azure first (Kudu console / SCM:
  https://paceforge-app.scm.azurewebsites.net  →  /home/data/paceforge.db),
then:

    python scripts/migrate_from_sqlite.py paceforge.db [--email you@example.com]

The old `user_data` JSON blobs are already in our Pydantic schema, so this is a
straight copy + pretty-print. Verify afterwards with `paceforge status`.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

# old column → new data file
MAPPING = {
    "profile_json": "profile.json",
    "plan_json": "plan.json",
    "activities_json": "activities.json",
    "hyrox_json": "hyrox.json",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db", help="path to the old paceforge.db")
    ap.add_argument("--email", help="which user to migrate (default: the first user)")
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row

    if args.email:
        user = con.execute("SELECT id, email FROM users WHERE email=?", (args.email,)).fetchone()
    else:
        user = con.execute("SELECT id, email FROM users ORDER BY id LIMIT 1").fetchone()
    if not user:
        print("No matching user.", file=sys.stderr)
        return 1
    print(f"Migrating user {user['email']} (id={user['id']})")

    ud = con.execute("SELECT * FROM user_data WHERE user_id=?", (user["id"],)).fetchone()
    if not ud:
        print("No user_data row for that user.", file=sys.stderr)
        return 1

    out = Path(args.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    cols = set(ud.keys())
    for col, fname in MAPPING.items():
        raw = ud[col] if col in cols else None
        if not raw:
            continue
        (out / fname).write_text(json.dumps(json.loads(raw), indent=2))
        print(f"  wrote {out / fname}")

    con.close()
    print("Done. Run `paceforge status` to confirm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
