"""PaceForge CLI — thin wrapper over :mod:`paceforge.actions`.

    paceforge login                 # one-time Garmin auth → prints GARMIN_TOKEN
    paceforge sync                  # pull Garmin metrics+activities → data/*.json
    paceforge status                # show stored profile + plan summary
    paceforge analyze               # full analytics over the stored profile
    paceforge validate              # check data/plan.json against the rules
    paceforge push [--week N] [--dry-run]   # push a plan week to Garmin
    paceforge strava-recent [--limit N]
    paceforge strava-set-description --activity-id ID --text "..."
"""

from __future__ import annotations

import argparse
import json
import sys

from paceforge import actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paceforge", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("login", help="one-time Garmin login (handles MFA)")
    p_sync = sub.add_parser("sync", help="pull Garmin metrics + activities")
    p_sync.add_argument("--lookback-days", type=int, default=90)
    p_plan = sub.add_parser("plan", help="scaffold a deterministic baseline plan")
    p_plan.add_argument("--goal", required=True,
                        choices=["5K", "10K", "HALF_MARATHON", "MARATHON", "HYROX"])
    p_plan.add_argument("--date", required=True, help="race date YYYY-MM-DD")
    p_plan.add_argument("--level", default="intermediate",
                        choices=["beginner", "intermediate", "advanced"])
    p_plan.add_argument("--days", default="tuesday,thursday,saturday,sunday",
                        help="comma-separated training days")
    p_plan.add_argument("--long-run-day", default="sunday")
    p_plan.add_argument("--target-time", type=float, default=None, help="goal finish seconds")
    sub.add_parser("status", help="show stored profile + plan summary")
    sub.add_parser("analyze", help="run analytics over the stored profile")
    sub.add_parser("validate", help="validate data/plan.json")

    p_push = sub.add_parser("push", help="push a plan week to Garmin")
    p_push.add_argument("--week", type=int, default=None)
    p_push.add_argument("--dry-run", action="store_true")

    p_sr = sub.add_parser("strava-recent", help="list recent Strava activities")
    p_sr.add_argument("--limit", type=int, default=10)
    p_sd = sub.add_parser("strava-set-description", help="set a Strava activity description")
    p_sd.add_argument("--activity-id", type=int, required=True)
    p_sd.add_argument("--text", required=True)

    args = parser.parse_args(argv)

    try:
        if args.cmd == "login":
            token = actions.login()
            print("\nGarmin login OK. Store this as the GARMIN_TOKEN secret:\n")
            print(token)
            return 0
        if args.cmd == "sync":
            _emit(actions.sync(lookback_days=args.lookback_days))
        elif args.cmd == "plan":
            _emit(actions.scaffold({
                "goal_type": args.goal,
                "target_date": args.date,
                "experience_level": args.level,
                "training_days": [d.strip() for d in args.days.split(",")],
                "long_run_day": args.long_run_day,
                "target_time_seconds": args.target_time,
            }))
        elif args.cmd == "status":
            _emit(actions.status())
        elif args.cmd == "analyze":
            _emit(actions.analyze())
        elif args.cmd == "validate":
            issues = actions.validate()
            if issues:
                print("INVALID:")
                for i in issues:
                    print(f"  - {i}")
                return 1
            print("valid")
        elif args.cmd == "push":
            _emit(actions.push(week=args.week, dry_run=args.dry_run))
        elif args.cmd == "strava-recent":
            _emit(actions.strava_recent(limit=args.limit))
        elif args.cmd == "strava-set-description":
            _emit(actions.strava_update_description(args.activity_id, args.text))
    except (RuntimeError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


def _emit(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
