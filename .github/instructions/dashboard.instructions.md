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
