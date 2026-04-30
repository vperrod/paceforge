Monolithic FastAPI file (~3500 lines). All endpoints live here, grouped by section headers.

## Section Map

| Line~ | Section | Description |
|-------|---------|-------------|
| 95 | Per-user state | In-memory dicts keyed by user_id (`_user_garmin`, `_user_coaches`, etc.) |
| 220 | Auth dependencies | `get_current_user`, `require_admin` |
| 277 | Public auth endpoints | `/register`, `/login`, `/token/refresh`, `/forgot-password`, `/reset-password` |
| 460 | Admin endpoints | User approval, listing, admin operations |
| 505 | Request/Response models | Inline Pydantic models for endpoint payloads |
| 586 | Garmin helpers | `_token_dir_for()`, `_ensure_garmin()` |
| 593 | Garmin endpoints | `/garmin/*` — sync activities, push workouts |
| 658 | Protected endpoints | Plan generation, profile, activity details |
| 1505 | Weekly Overview | Weekly training summary/analysis |
| 1918 | HYROX endpoints | `/hyrox/*` — scrape results, analyse races |
| 2104 | Friends | `/friends/*` — send/accept/list friend requests |
| 2235 | Feed | `/feed/*` — social feed events, likes, comments |
| 2349 | Strava | `/strava/*` — OAuth flow, activity sync |
| 2795 | Health Data | `/health/*` — Apple Health / Google Health Connect |
| 2875 | Diet & Nutrition | `/diet/*` — meal plans, macros, weight tracking |
| 3418 | Mobile Web SPA | Serves `/m/` static files |

## Conventions

- Every protected endpoint uses `user: dict = Depends(get_current_user)`.
- Admin endpoints use `user: dict = Depends(require_admin)`.
- New endpoints go in the matching section above.
- User data is stored as JSON blobs in SQLite via `save_user_data()` / `get_user_data()`.
- AI responses are parsed with `json.loads()` + `json_repair` fallback. Always backfill missing fields.
