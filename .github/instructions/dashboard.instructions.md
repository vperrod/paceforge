Monolithic Streamlit file (~6500 lines). All UI lives here with tab-based navigation.

## Tab Map

| Index | Variable | Tab Name | Line~ | Sub-tabs |
|-------|----------|----------|-------|----------|
| 0 | `tab_feed` | Feed | 2059 | — |
| 1 | `tab_profile` | Fitness Profile | 2615 | Weekly Overview, Snapshot, Aerobic Engine, Running Economy, Load & Recovery, Race Predictions, Recommendations, Trends |
| 2 | `tab_plan` | Training Plan | 3732 | — |
| 3 | `tab_calendar` | Calendar | 4334 | — |
| 4 | `tab_hyrox` | HYROX | 5468 | — |
| 5 | `tab_diet` | Diet & Nutrition | 6162 | Nutrition Plan, Macro Tracker, Weight Progress, Preferences |
| 6 | `tab_coach` | AI Coach | 6512 | — |
| 7 | `tab_user_settings` | User Profile | 6543 | Account, Friends, Connections |
| 8 | `tab_admin` | Admin Panel | 6992 | (admin only) |

## Key Helpers

- `API_BASE = "http://localhost:8000"` — all API calls go to local FastAPI
- `_auth_headers()` — returns `{"Authorization": "Bearer {jwt}"}` from session state
- `_error_detail(r)` — safely extracts error from response JSON or falls back to `r.text`
- `_fmt_pace(sec_per_km)` — formats seconds-per-km to `M:SS/km`
- `_fmt_duration(seconds)` — formats seconds to human-readable duration
- `_logout()` — clears session state and cookies

## Conventions

- API calls: `requests.get/post(f"{API_BASE}/endpoint", headers=_auth_headers(), timeout=N)`
- Display errors with `st.error(_error_detail(r))`
- Session state keys: `st.session_state.jwt`, `st.session_state.user_name`, `st.session_state.role`
- Charts use Plotly (`plotly.graph_objects` / `plotly.express`)
- New tabs: add name to `tab_names` list (~line 2042), unpack in `st.tabs()`, add `with tab_xxx:` block

## Training Plan Tab

### Editable Paces

Pace zones (Easy, Marathon, Threshold, Interval) are editable `st.text_input` fields displaying `M:SS` format (e.g. `5:30`). Session state keys: `pace_{plan_id}_{pace_key}` (e.g. `pace_abc123_easy_pace`). When "Adapt Plan" is clicked, the M:SS values are parsed to seconds and sent as JSON body to `/plan/adapt`. If parsing fails or values haven't changed, the API falls back to VDOT auto-calculation. The API preserves `plan.accepted` state on adaptation.

### Calendar Tab

`st_calendar()` must use `callbacks=["eventClick", "eventChange"]` — do NOT include `eventsSet` (it fires on every rerender since streamlit-calendar 1.3.2 and overwrites click/drag events). Planned workout detail panel shows a color-coded workout type badge from `_WORKOUT_COLORS`. Calendar event colors and `editable` flag depend on `plan.accepted` — accepted plan events get workout-type colors and are draggable, pending plans are muted grey (`#3E4455`) and non-draggable.
