"""PaceForge — Streamlit Dashboard (Dark Modern UI)."""

from __future__ import annotations

import base64
import json
from datetime import date, timedelta
from pathlib import Path

import extra_streamlit_components as stx
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="PaceForge", page_icon="🏃", layout="wide")

# ── Cookie manager for persistent JWT ────────────────────────────────
_cookie_mgr = stx.CookieManager(key="pf_cookies")

# ═══════════════════════════════════════════════════════════════════════
# LOGO — load SVG and encode as base64 data URI
# ═══════════════════════════════════════════════════════════════════════

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.svg"
if _LOGO_PATH.exists():
    _LOGO_B64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
    _LOGO_URI = f"data:image/svg+xml;base64,{_LOGO_B64}"
else:
    _LOGO_URI = ""

# ═══════════════════════════════════════════════════════════════════════
# CUSTOM CSS — dark modern theme overrides
# ═══════════════════════════════════════════════════════════════════════

_CUSTOM_CSS = """
<style>
/* ── Global ──────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px;
}

/* ── Cards ───────────────────────────────────────────── */
.pf-card {
    background: #242830;
    border: 1px solid #2D3139;
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.pf-card:hover {
    border-color: #3A3F4B;
}

/* ── Metric cards ────────────────────────────────────── */
.pf-metric-card {
    background: #242830;
    border: 1px solid #2D3139;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.pf-metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 14px 14px 0 0;
}
.pf-metric-card.green::before { background: #00D26A; }
.pf-metric-card.blue::before { background: #2196F3; }
.pf-metric-card.orange::before { background: #FF9800; }
.pf-metric-card.purple::before { background: #AB47BC; }
.pf-metric-card.red::before { background: #F44336; }
.pf-metric-card.cyan::before { background: #00BCD4; }
.pf-metric-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8B92A5;
    margin-bottom: 0.4rem;
}
.pf-metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #FAFAFA;
    line-height: 1.1;
}
.pf-metric-unit {
    font-size: 0.8rem;
    font-weight: 400;
    color: #8B92A5;
    margin-left: 0.2rem;
}

/* ── Logo / Brand ────────────────────────────────────── */
.pf-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}
.pf-brand img {
    width: 42px;
    height: 42px;
}
.pf-brand-text {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #FAFAFA;
}
.pf-brand-text span {
    color: #00D26A;
}

/* ── Auth page ───────────────────────────────────────── */
.pf-auth-container {
    max-width: 420px;
    margin: 4rem auto;
}
.pf-auth-header {
    text-align: center;
    margin-bottom: 2rem;
}
.pf-auth-header img {
    width: 72px;
    height: 72px;
    margin-bottom: 1rem;
}
.pf-auth-header h1 {
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    margin: 0;
    color: #FAFAFA;
}
.pf-auth-header h1 span {
    color: #00D26A;
}
.pf-auth-header p {
    color: #8B92A5;
    font-size: 0.9rem;
    margin-top: 0.5rem;
}

/* ── Sidebar ─────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #1E2128 !important;
    border-right: 1px solid #2D3139;
}
section[data-testid="stSidebar"] .pf-user-badge {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: #242830;
    border-radius: 12px;
    margin-bottom: 1rem;
}
.pf-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #00D26A;
    color: #1A1D23;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
    flex-shrink: 0;
}
.pf-user-name {
    font-weight: 600;
    font-size: 0.9rem;
    color: #FAFAFA;
}
.pf-user-role {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8B92A5;
}
.pf-garmin-card {
    background: #242830;
    border: 1px solid #2D3139;
    border-radius: 12px;
    padding: 1rem;
    margin-top: 0.5rem;
}
.pf-garmin-connected {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #00D26A;
    font-weight: 600;
    font-size: 0.85rem;
}
.pf-garmin-connected::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00D26A;
    box-shadow: 0 0 6px #00D26A;
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: #00D26A !important;
    color: #1A1D23 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    background: #00B85C !important;
    box-shadow: 0 4px 12px rgba(0, 210, 106, 0.3) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #3A3F4B !important;
    border-radius: 8px !important;
    color: #FAFAFA !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #00D26A !important;
    color: #00D26A !important;
}

/* ── Tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #2D3139;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent;
    padding: 0.75rem 1.25rem !important;
    font-weight: 500;
    color: #8B92A5 !important;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    border-bottom-color: #00D26A !important;
    color: #FAFAFA !important;
    font-weight: 600;
}

/* ── Inputs ──────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #1A1D23 !important;
    border: 1px solid #2D3139 !important;
    border-radius: 8px !important;
    color: #FAFAFA !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00D26A !important;
    box-shadow: 0 0 0 1px #00D26A !important;
}

/* ── Status badges ───────────────────────────────────── */
.pf-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.pf-badge.pending { background: rgba(255,152,0,0.15); color: #FF9800; }
.pf-badge.approved { background: rgba(0,210,106,0.15); color: #00D26A; }
.pf-badge.rejected { background: rgba(244,67,54,0.15); color: #F44336; }
.pf-badge.admin { background: rgba(171,71,188,0.15); color: #AB47BC; }

/* ── Workout pills ───────────────────────────────────── */
.pf-workout-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.75rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 0.2rem 0.2rem 0.2rem 0;
}

/* ── Training pace cards ─────────────────────────────── */
.pf-pace-card {
    background: #242830;
    border: 1px solid #2D3139;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    text-align: center;
}
.pf-pace-zone {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.3rem;
}
.pf-pace-value {
    font-size: 1.2rem;
    font-weight: 700;
    color: #FAFAFA;
}

/* ── Coach chat ──────────────────────────────────────── */
.pf-chat-bubble {
    background: #242830;
    border: 1px solid #2D3139;
    border-radius: 14px 14px 14px 4px;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    line-height: 1.6;
}

/* ── Activity table ──────────────────────────────────── */
.pf-activity-row {
    display: flex;
    align-items: center;
    padding: 0.6rem 0;
    border-bottom: 1px solid #2D3139;
    font-size: 0.85rem;
}
.pf-activity-row:last-child { border-bottom: none; }
.pf-activity-name { flex: 2; font-weight: 500; color: #FAFAFA; }
.pf-activity-dist { flex: 1; color: #8B92A5; text-align: right; }
.pf-activity-pace { flex: 1; color: #00D26A; text-align: right; font-weight: 600; }

/* ── Week cards ──────────────────────────────────────── */
.pf-week-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
}
.pf-week-title {
    font-weight: 700;
    font-size: 1rem;
    color: #FAFAFA;
}
.pf-week-meta {
    font-size: 0.8rem;
    color: #8B92A5;
}
.pf-week-phase {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: rgba(0,210,106,0.12);
    color: #00D26A;
}
.pf-workout-item {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(45,49,57,0.5);
}
.pf-workout-item:last-child { border-bottom: none; }
.pf-workout-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-top: 0.35rem;
    flex-shrink: 0;
}
.pf-workout-info { flex: 1; }
.pf-workout-name { font-weight: 600; font-size: 0.88rem; color: #FAFAFA; }
.pf-workout-detail { font-size: 0.78rem; color: #8B92A5; margin-top: 0.15rem; }

/* ── User cards (admin) ──────────────────────────────── */
.pf-user-card {
    background: #242830;
    border: 1px solid #2D3139;
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* ── Section headers ─────────────────────────────────── */
.pf-section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #FAFAFA;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #2D3139;
}

/* ── Scrollbar ───────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #1A1D23; }
::-webkit-scrollbar-thumb { background: #3A3F4B; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #555; }

/* ── Misc polish ─────────────────────────────────────── */
.stDivider { border-color: #2D3139 !important; }
hr { border-color: #2D3139 !important; }

/* Hide Streamlit default header/footer */
#MainMenu { visibility: hidden; }
header { visibility: hidden; }
footer { visibility: hidden; }

/* ── Mobile Responsive ─────────────────────────────────────────────── */
@media (max-width: 768px) {
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    .pf-card { padding: 0.75rem !important; border-radius: 10px !important; }
    .pf-metric-card { padding: 0.6rem !important; min-width: unset !important; }
    .pf-pace-card { padding: 0.5rem !important; }
    .pf-pace-value { font-size: 1.2rem !important; }
    .pf-section-header { font-size: 1rem !important; }
    .pf-workout-item { padding: 0.4rem 0 !important; }
    .pf-workout-name { font-size: 0.85rem !important; }
    .pf-workout-detail { font-size: 0.75rem !important; }
    .pf-activity-row { flex-wrap: wrap !important; gap: 0.25rem !important; padding: 0.4rem 0 !important; }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    .fc .fc-toolbar { flex-wrap: wrap !important; gap: 0.25rem !important; }
    .fc .fc-toolbar-title { font-size: 1rem !important; }
    .fc .fc-button { padding: 0.2rem 0.4rem !important; font-size: 0.75rem !important; }
    .fc .fc-daygrid-event { font-size: 0.7rem !important; }
}
@media (max-width: 480px) {
    .pf-metric-card .pf-metric-value { font-size: 1.5rem !important; }
    .pf-pace-value { font-size: 1rem !important; }
    .fc .fc-toolbar-title { font-size: 0.85rem !important; }
}
</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# HELPER: HTML rendering functions
# ═══════════════════════════════════════════════════════════════════════

def _render_brand(size: str = "normal") -> str:
    """Return brand HTML with logo + wordmark."""
    if size == "large":
        img = f'<img src="{_LOGO_URI}" style="width:72px;height:72px;">' if _LOGO_URI else ""
        return f"""
        <div style="text-align:center;margin-bottom:1.5rem;">
            {img}
            <h1 style="font-size:2rem;font-weight:700;letter-spacing:0.12em;margin:0.5rem 0 0 0;">
                PACE<span style="color:#00D26A;">FORGE</span>
            </h1>
            <p style="color:#8B92A5;font-size:0.9rem;margin-top:0.4rem;">
                AI-Powered Running Plan Generator
            </p>
        </div>"""
    img = f'<img src="{_LOGO_URI}" style="width:36px;height:36px;">' if _LOGO_URI else ""
    return f"""
    <div class="pf-brand">
        {img}
        <div class="pf-brand-text">PACE<span>FORGE</span></div>
    </div>"""


def _metric_card(label: str, value: str, unit: str = "", color: str = "green") -> str:
    unit_html = f'<span class="pf-metric-unit">{unit}</span>' if unit else ""
    return f"""
    <div class="pf-metric-card {color}">
        <div class="pf-metric-label">{label}</div>
        <div class="pf-metric-value">{value}{unit_html}</div>
    </div>"""


_WORKOUT_COLORS = {
    "easy_run": "#4CAF50",
    "recovery_run": "#81C784",
    "easy_with_strides": "#66BB6A",
    "long_run": "#2196F3",
    "long_run_progressive": "#1976D2",
    "long_run_with_race_pace": "#1565C0",
    "tempo": "#FF9800",
    "threshold": "#F57C00",
    "intervals": "#F44336",
    "vo2max": "#D32F2F",
    "speed": "#E53935",
    "hills": "#C62828",
    "fartlek": "#FF7043",
    "progressive": "#FFA726",
    "race_pace": "#EF6C00",
    "rest": "#9E9E9E",
}

_PACE_COLORS = {
    "Easy": "#4CAF50",
    "Marathon": "#2196F3",
    "Threshold": "#FF9800",
    "Interval": "#F44336",
}

_PHASE_COLORS = {
    "base": "rgba(0,210,106,0.12)",
    "build": "rgba(33,150,243,0.12)",
    "peak": "rgba(255,152,0,0.12)",
    "taper": "rgba(171,71,188,0.12)",
    "race": "rgba(244,67,54,0.12)",
}

_PHASE_TEXT = {
    "base": "#00D26A",
    "build": "#2196F3",
    "peak": "#FF9800",
    "taper": "#AB47BC",
    "race": "#F44336",
}

# ── Session state defaults ───────────────────────────────────────────

for key, default in {
    "jwt": None,
    "role": None,
    "user_name": None,
    "user_email": None,
    "garmin_logged_in": False,
    "mfa_required": False,
    "profile": None,
    "plans": [],
    "page": "login",
    "_restored": False,
    "cal_selected_event": None,
    "cal_selected_detail": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Restore JWT from cookie on fresh page load ──────────────────────
if st.session_state.jwt is None:
    saved_jwt = _cookie_mgr.get("pf_jwt")
    if saved_jwt:
        # Validate the token is still accepted by the API
        try:
            r = requests.get(
                f"{API_BASE}/auth/profile",
                headers={"Authorization": f"Bearer {saved_jwt}"},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                st.session_state.jwt = saved_jwt
                st.session_state.role = data.get("role", "user")
                st.session_state.user_name = data.get("name", "")
                st.session_state.user_email = data.get("email", "")
                st.session_state.page = "app"
        except Exception:
            pass  # Cookie invalid or API unreachable — show login


def _auth_headers() -> dict:
    if st.session_state.jwt:
        return {"Authorization": f"Bearer {st.session_state.jwt}"}
    return {}


def _logout():
    for key in ["jwt", "role", "user_name", "user_email", "garmin_logged_in", "mfa_required", "profile", "plans"]:
        st.session_state[key] = None if key not in ("garmin_logged_in", "mfa_required", "plans") else (False if key != "plans" else [])
    st.session_state._restored = False
    st.session_state.page = "login"
    _cookie_mgr.delete("pf_jwt")


def _error_detail(r: requests.Response) -> str:
    """Safely extract error detail from a response."""
    try:
        return r.json().get("detail", r.text)
    except Exception:
        return r.text or f"HTTP {r.status_code}"


def _fmt_pace(sec_per_km: float | int | None) -> str:
    """Convert seconds-per-km to 'M:SS/km' string."""
    if not sec_per_km:
        return "—"
    m = int(sec_per_km) // 60
    s = int(sec_per_km) % 60
    return f"{m}:{s:02d}/km"


def _fmt_duration(seconds: float | int | None) -> str:
    if not seconds:
        return "—"
    seconds = int(seconds)
    if seconds >= 3600:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def _fmt_dist(meters: float | int | None) -> str:
    if not meters:
        return "—"
    km = meters / 1000
    return f"{km:.1f}km" if km >= 1 else f"{int(meters)}m"


def _render_step_line(step: dict) -> str:
    """Render a single workout step as a human-readable line."""
    stype = step.get("step_type", "active").lower()
    dist = step.get("distance_meters")
    dur = step.get("duration_seconds")
    target_type = (step.get("target_type") or "").lower()
    target_low = step.get("target_low")

    dist_str = _fmt_dist(dist) if dist else (_fmt_duration(dur) if dur else "")

    if stype == "warmup":
        pace_hint = f" (no faster than {_fmt_pace(target_low)})" if target_low else ""
        return f"🟢 <b>{dist_str}</b> warm up at a conversational pace{pace_hint}"
    elif stype == "cooldown":
        return f"🔵 <b>{dist_str}</b> cool down at a conversational pace (or slower!)"
    elif stype == "recovery":
        return f"⚪ <b>{dist_str}</b> recovery jog"
    elif stype == "rest":
        return f"⚪ <b>{dist_str}</b> walking rest"
    else:  # active / interval leaf
        if target_type == "pace" and target_low:
            return f"🔴 <b>{dist_str}</b> at {_fmt_pace(target_low)}"
        elif target_type == "open" or not target_low:
            return f"🟢 <b>{dist_str}</b> at an easy, conversational pace"
        else:
            return f"🟠 <b>{dist_str}</b> at {_fmt_pace(target_low)}"


def _render_workout_detail(workout: dict, plan_paces: dict | None = None) -> str:
    """Render a structured workout description as HTML."""
    steps = workout.get("steps", [])
    name = workout.get("name", "Workout")
    purpose = workout.get("purpose", "")
    workout.get("workout_type", "")
    est_dist = _fmt_dist(workout.get("estimated_distance_meters"))
    est_dur = _fmt_duration(workout.get("estimated_duration_seconds"))
    notes = workout.get("notes", "")

    lines = []
    lines.append(f'<div style="font-weight:700;font-size:1.1rem;margin-bottom:0.5rem;">{name}</div>')
    if purpose:
        lines.append(f'<div style="color:#8B92A5;margin-bottom:0.75rem;font-size:0.85rem;">{purpose}</div>')

    # Summary badges
    badges = []
    if est_dist and est_dist != "—":
        badges.append(f'<span style="background:#242830;padding:4px 10px;border-radius:12px;font-size:0.8rem;margin-right:6px;">📏 {est_dist}</span>')
    if est_dur and est_dur != "—":
        badges.append(f'<span style="background:#242830;padding:4px 10px;border-radius:12px;font-size:0.8rem;margin-right:6px;">⏱ {est_dur}</span>')
    if badges:
        lines.append(f'<div style="margin-bottom:0.75rem;">{"".join(badges)}</div>')

    if not steps:
        lines.append('<div style="color:#8B92A5;">No structured steps available.</div>')
    else:
        lines.append('<div style="font-weight:600;font-size:0.9rem;margin-bottom:0.5rem;color:#00D26A;">Workout Structure</div>')
        for step in steps:
            rc = step.get("repeat_count")
            nested = step.get("steps", [])
            if rc and nested:
                lines.append(
                    f'<div style="margin:0.5rem 0;padding:0.5rem 0.75rem;border-left:3px solid #FF9800;background:#242830;border-radius:0 8px 8px 0;">'
                    f'<div style="font-weight:600;color:#FF9800;margin-bottom:0.25rem;">Repeat {rc}×</div>'
                )
                for sub in nested:
                    lines.append(f'<div style="padding:2px 0;">{_render_step_line(sub)}</div>')
                lines.append("</div>")
            else:
                lines.append(f'<div style="padding:3px 0;">{_render_step_line(step)}</div>')

    if notes:
        lines.append(f'<div style="margin-top:0.75rem;color:#8B92A5;font-size:0.8rem;font-style:italic;">💡 {notes}</div>')

    return f'<div class="pf-card" style="margin-top:1rem;">{"".join(lines)}</div>'


def _render_garmin_activity_detail(detail: dict) -> None:
    """Render Garmin activity detail with splits, charts, and HR zones."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    raw_summary = detail.get("summary") or {}
    # Garmin nests metrics inside summaryDTO; fall back to top-level if absent
    summary = raw_summary.get("summaryDTO") or raw_summary
    splits_data = detail.get("splits") or {}
    hr_zones_data = detail.get("hr_zones") or {}
    weather_data = detail.get("weather") or {}

    # ── Summary metric cards ──
    total_dist = summary.get("distance", 0)
    total_dur = summary.get("duration", 0)
    avg_speed = summary.get("averageSpeed", 0)
    avg_pace = (1000 / avg_speed) if avg_speed else 0
    avg_hr = summary.get("averageHR")
    max_hr = summary.get("maxHR")
    calories = summary.get("calories")
    elevation = summary.get("elevationGain")
    cadence = summary.get("averageRunningCadenceInStepsPerMinute")
    aero_te = summary.get("aerobicTrainingEffect")
    anaero_te = summary.get("anaerobicTrainingEffect")

    cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:0.4rem;margin-bottom:0.75rem;">'
    metric_data = [
        ("Distance", _fmt_dist(total_dist), "📏"),
        ("Duration", _fmt_duration(total_dur / 1000 if total_dur > 10000 else total_dur), "⏱"),
        ("Avg Pace", _fmt_pace(avg_pace) if avg_pace else "—", "🏃"),
    ]
    if avg_hr:
        metric_data.append(("Avg HR", f"{int(avg_hr)} bpm", "❤️"))
    if max_hr:
        metric_data.append(("Max HR", f"{int(max_hr)} bpm", "💓"))
    if cadence:
        metric_data.append(("Cadence", f"{int(cadence * 2)} spm", "🦶"))
    if calories:
        metric_data.append(("Calories", f"{int(calories)}", "🔥"))
    if elevation:
        metric_data.append(("Elevation", f"{int(elevation)}m", "⛰️"))
    if aero_te:
        metric_data.append(("Aerobic TE", f"{aero_te:.1f}", "🫁"))
    if anaero_te:
        metric_data.append(("Anaerobic TE", f"{anaero_te:.1f}", "💪"))

    for label, val, icon in metric_data:
        cards_html += (
            f'<div style="background:#242830;border-radius:8px;padding:0.4rem;text-align:center;">'
            f'<div style="font-size:0.65rem;color:#8B92A5;">{icon} {label}</div>'
            f'<div style="font-size:0.9rem;font-weight:700;color:#FAFAFA;">{val}</div>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── Weather info ──
    if weather_data and isinstance(weather_data, dict):
        temp = weather_data.get("temp")
        cond = weather_data.get("weatherTypeDTO", {}).get("desc") if isinstance(weather_data.get("weatherTypeDTO"), dict) else None
        humidity = weather_data.get("relativeHumidity")
        wind = weather_data.get("windSpeed")
        parts = []
        if temp is not None:
            parts.append(f"🌡️ {temp}°C")
        if cond:
            parts.append(cond)
        if humidity is not None:
            parts.append(f"💧 {humidity}%")
        if wind is not None:
            parts.append(f"💨 {wind} km/h")
        if parts:
            st.markdown(
                f'<div style="color:#8B92A5;font-size:0.75rem;margin-bottom:0.5rem;">{" · ".join(parts)}</div>',
                unsafe_allow_html=True,
            )

    # ── Splits ──
    laps = splits_data.get("lapDTOs") or []
    if laps:
        split_nums = []
        paces = []
        hrs = []
        rows_html = '<table style="width:100%;border-collapse:collapse;font-size:0.75rem;"><tr style="color:#8B92A5;border-bottom:1px solid #2D3139;"><th style="text-align:left;padding:3px;">Split</th><th>Dist</th><th>Pace</th><th>HR</th></tr>'

        for i, lap in enumerate(laps, 1):
            lap_dist = lap.get("distance", 0)
            lap_speed = lap.get("averageSpeed", 0)
            lap_pace = (1000 / lap_speed) if lap_speed else 0
            lap_hr = lap.get("averageHR", 0)

            split_nums.append(i)
            paces.append(lap_pace)
            hrs.append(lap_hr)

            rows_html += (
                f'<tr style="border-bottom:1px solid #2D3139;">'
                f'<td style="padding:3px;font-weight:600;">{i}</td>'
                f'<td style="text-align:center;">{_fmt_dist(lap_dist)}</td>'
                f'<td style="text-align:center;">{_fmt_pace(lap_pace)}</td>'
                f'<td style="text-align:center;">{int(lap_hr) if lap_hr else "—"}</td>'
                f'</tr>'
            )
        rows_html += '</table>'
        st.markdown(f'<div class="pf-card" style="margin-bottom:0.5rem;padding:0.5rem;">{rows_html}</div>', unsafe_allow_html=True)

        # Combined pace + HR chart over splits
        if paces and any(h > 0 for h in hrs):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            avg_p = sum(paces) / len(paces)
            colors = ["#00D26A" if p <= avg_p else "#FF5252" for p in paces]

            fig.add_trace(
                go.Bar(
                    x=split_nums, y=paces, name="Pace",
                    marker_color=colors,
                    text=[_fmt_pace(p) for p in paces],
                    textposition="outside",
                    textfont=dict(color="#FAFAFA", size=9),
                ),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(
                    x=split_nums, y=hrs, name="Heart Rate",
                    mode="lines+markers",
                    line=dict(color="#FF5252", width=2),
                    marker=dict(size=5),
                ),
                secondary_y=True,
            )
            fig.update_layout(
                plot_bgcolor="#1A1D23", paper_bgcolor="#1A1D23", font_color="#FAFAFA",
                margin=dict(l=40, r=40, t=25, b=35), height=240,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
                bargap=0.3,
            )
            fig.update_yaxes(autorange="reversed", title_text="Pace (s/km)", gridcolor="#2D3139", secondary_y=False)
            fig.update_yaxes(title_text="HR (bpm)", gridcolor="#2D3139", secondary_y=True)
            fig.update_xaxes(title_text="Split", gridcolor="#2D3139", dtick=1)
            st.plotly_chart(fig, use_container_width=True, key="splits_hr_chart")
        elif paces:
            # Pace only (no HR data)
            avg_p = sum(paces) / len(paces)
            colors = ["#00D26A" if p <= avg_p else "#FF5252" for p in paces]
            fig = go.Figure(go.Bar(
                x=split_nums, y=paces, marker_color=colors,
                text=[_fmt_pace(p) for p in paces], textposition="outside",
                textfont=dict(color="#FAFAFA", size=9),
            ))
            fig.update_layout(
                plot_bgcolor="#1A1D23", paper_bgcolor="#1A1D23", font_color="#FAFAFA",
                margin=dict(l=40, r=20, t=25, b=35), height=220,
                yaxis=dict(autorange="reversed", title="Pace (s/km)", gridcolor="#2D3139"),
                xaxis=dict(gridcolor="#2D3139", dtick=1, title="Split"), bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True, key="splits_chart")

    # ── HR Zones ──
    hr_list = hr_zones_data if isinstance(hr_zones_data, list) else hr_zones_data.get("hrTimeInZones", [])
    if hr_list:
        st.markdown('<div style="font-weight:600;font-size:0.85rem;margin-bottom:0.3rem;color:#00D26A;">Heart Rate Zones</div>', unsafe_allow_html=True)
        zone_labels = []
        zone_seconds = []
        zone_colors_list = ["#3F51B5", "#2196F3", "#4CAF50", "#FF9800", "#F44336"]
        for zd in hr_list:
            zn = zd.get("zoneNumber") or zd.get("zone", 0)
            secs = zd.get("secsInZone", 0)
            zone_labels.append(f"Z{zn}")
            zone_seconds.append(secs)

        fig_hr = go.Figure(go.Bar(
            y=zone_labels, x=zone_seconds, orientation="h",
            marker_color=zone_colors_list[:len(zone_labels)],
            text=[_fmt_duration(s) for s in zone_seconds],
            textposition="auto", textfont=dict(color="#FAFAFA", size=9),
        ))
        fig_hr.update_layout(
            plot_bgcolor="#1A1D23", paper_bgcolor="#1A1D23", font_color="#FAFAFA",
            margin=dict(l=30, r=20, t=10, b=25), height=160,
            xaxis=dict(title="Time (s)", gridcolor="#2D3139"),
            yaxis=dict(gridcolor="#2D3139"), bargap=0.3,
        )
        st.plotly_chart(fig_hr, use_container_width=True, key="hr_zones_chart")


# ═══════════════════════════════════════════════════════════════════════
# AUTH GATE
# ═══════════════════════════════════════════════════════════════════════

if st.session_state.jwt is None:
    # Centered auth container
    _left, auth_col, _right = st.columns([1, 1.2, 1])

    with auth_col:
        st.markdown(_render_brand("large"), unsafe_allow_html=True)

        if st.session_state.page == "register":
            st.markdown('<div class="pf-card">', unsafe_allow_html=True)
            st.markdown("#### Create Account")
            with st.form("register_form"):
                reg_name = st.text_input("Full Name")
                reg_email = st.text_input("Email")
                reg_password = st.text_input("Password (min 8 characters)", type="password")
                reg_confirm = st.text_input("Confirm Password", type="password")
                reg_reason = st.text_area(
                    "Why do you want access?",
                    placeholder="e.g. Training for my first marathon",
                    max_chars=500,
                )
                submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if submitted:
                if not reg_name or not reg_email or not reg_password:
                    st.error("All fields except reason are required.")
                elif len(reg_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        r = requests.post(
                            f"{API_BASE}/auth/register",
                            json={
                                "name": reg_name,
                                "email": reg_email,
                                "password": reg_password,
                                "reason": reg_reason,
                            },
                            timeout=15,
                        )
                        if r.status_code == 201:
                            st.success(
                                "Registration submitted! An admin will review your request. "
                                "You'll be able to log in once approved."
                            )
                        elif r.status_code == 409:
                            st.error("An account with this email already exists.")
                        else:
                            st.error(f"Registration failed: {_error_detail(r)}")
                    except requests.ConnectionError:
                        st.error("Cannot reach PaceForge API. Is the server running?")

            st.markdown("")
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()

        else:
            st.markdown('<div class="pf-card">', unsafe_allow_html=True)
            st.markdown("#### Welcome Back")
            with st.form("login_form"):
                login_email = st.text_input("Email")
                login_password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if login_submitted:
                try:
                    r = requests.post(
                        f"{API_BASE}/auth/login",
                        json={"email": login_email, "password": login_password},
                        timeout=15,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state.jwt = data["access_token"]
                        st.session_state.role = data["role"]
                        st.session_state.user_name = data["name"]
                        st.session_state.user_email = data.get("email", "")
                        st.session_state.page = "app"
                        _cookie_mgr.set("pf_jwt", data["access_token"], max_age=86400)
                        st.rerun()
                    elif r.status_code == 403:
                        st.warning(_error_detail(r))
                    else:
                        st.error(_error_detail(r))
                except requests.ConnectionError:
                    st.error("Cannot reach PaceForge API. Is the server running?")

            st.markdown("")
            st.markdown(
                '<p style="text-align:center;color:#8B92A5;font-size:0.85rem;">Don\'t have an account?</p>',
                unsafe_allow_html=True,
            )
            if st.button("Create Account", use_container_width=True):
                st.session_state.page = "register"
                st.rerun()

    st.stop()


# ═══════════════════════════════════════════════════════════════════════
# MAIN APP — authenticated
# ═══════════════════════════════════════════════════════════════════════

# ── Auto-restore Garmin connection, plan, and activities on load ─────
if not st.session_state._restored:
    st.session_state._restored = True
    try:
        # 1) Check Garmin connection (triggers auto-reconnect from cached tokens)
        r = requests.get(
            f"{API_BASE}/garmin/status",
            headers=_auth_headers(),
            timeout=15,
        )
        if r.status_code == 200:
            status_data = r.json()
            if status_data.get("connected"):
                st.session_state.garmin_logged_in = True
            st.session_state["last_synced"] = status_data.get("last_synced")

        # 2) Restore plans from DB cache
        if not st.session_state.plans:
            r = requests.get(
                f"{API_BASE}/plans",
                headers=_auth_headers(),
                timeout=10,
            )
            if r.status_code == 200:
                st.session_state.plans = r.json()

        # 3) Restore cached activities
        if not st.session_state.get("garmin_activities"):
            r = requests.get(
                f"{API_BASE}/activities?days=240",
                headers=_auth_headers(),
                timeout=30,
            )
            if r.status_code == 200:
                st.session_state["garmin_activities"] = r.json()

        # 4) Restore fitness profile
        if not st.session_state.get("profile"):
            r = requests.get(
                f"{API_BASE}/profile",
                headers=_auth_headers(),
                timeout=15,
            )
            if r.status_code == 200:
                st.session_state.profile = r.json()
    except Exception:
        pass  # Non-critical — user can manually sync

# ── Sidebar ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(_render_brand(), unsafe_allow_html=True)

    # User badge with avatar
    initials = "".join(w[0].upper() for w in (st.session_state.user_name or "U").split()[:2])
    role_label = st.session_state.role or "user"
    st.markdown(
        f"""<div class="pf-user-badge">
            <div class="pf-avatar">{initials}</div>
            <div>
                <div class="pf-user-name">{st.session_state.user_name}</div>
                <div class="pf-user-role">{role_label}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Garmin status indicator in sidebar
    if st.session_state.garmin_logged_in:
        st.markdown(
            '<div style="background:#00D26A22;color:#00D26A;padding:6px 12px;border-radius:8px;'
            'font-size:0.8rem;font-weight:600;text-align:center;margin-bottom:0.5rem;">'
            '⌚ Garmin Connected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#FF980022;color:#FF9800;padding:6px 12px;border-radius:8px;'
            'font-size:0.8rem;font-weight:600;text-align:center;margin-bottom:0.5rem;">'
            '⌚ Garmin Not Connected</div>',
            unsafe_allow_html=True,
        )

    if st.button("Logout", use_container_width=True):
        _logout()
        st.rerun()


# ── Garmin Sync Status Banner ──────────────────────────────────────

if not st.session_state.garmin_logged_in:
    last_synced = st.session_state.get("last_synced")
    sync_msg = ""
    if last_synced:
        try:
            from datetime import datetime as _dt
            ts = _dt.fromisoformat(last_synced.replace("Z", "+00:00"))
            sync_msg = f" · Last synced: {ts.strftime('%b %d, %Y %H:%M UTC')}"
        except Exception:
            sync_msg = f" · Last synced: {last_synced[:19]}"
    st.markdown(
        f'<div style="background:#2D2000;border:1px solid #FF9800;border-radius:8px;'
        f'padding:0.5rem 1rem;margin-bottom:1rem;color:#FFB74D;font-size:0.85rem;">'
        f'⚠️ Garmin not connected — showing cached data{sync_msg}. '
        f'Connect via the sidebar to refresh.</div>',
        unsafe_allow_html=True,
    )
else:
    last_synced = st.session_state.get("last_synced")
    if last_synced:
        try:
            from datetime import datetime as _dt
            ts = _dt.fromisoformat(last_synced.replace("Z", "+00:00"))
            sync_text = f"Last synced: {ts.strftime('%b %d, %Y %H:%M UTC')}"
        except Exception:
            sync_text = f"Last synced: {last_synced[:19]}"
        st.markdown(
            f'<div style="background:#0D2818;border:1px solid #00D26A;border-radius:8px;'
            f'padding:0.5rem 1rem;margin-bottom:1rem;color:#69F0AE;font-size:0.85rem;">'
            f'✅ Garmin connected · {sync_text}</div>',
            unsafe_allow_html=True,
        )


# ── User Dashboard Header ────────────────────────────────────────────

_user_display_name = st.session_state.user_name or "Runner"
_header_initials = "".join(w[0].upper() for w in _user_display_name.split()[:2]) if _user_display_name else "?"
_p = st.session_state.profile

# Find today's workout from the accepted plan
_today_str = str(date.today())
_today_workout = None
for _plan in (st.session_state.plans or []):
    if isinstance(_plan, dict) and _plan.get("accepted"):
        for _wk in _plan.get("weeks", []):
            for _wo in _wk.get("workouts", []):
                if str(_wo.get("scheduled_date", "")) == _today_str:
                    _today_workout = _wo
                    break

# Build stat pills
_header_stats = []
if _p:
    if _p.get("vo2_max"):
        _header_stats.append(("VO\u2082", str(_p["vo2_max"]), "#00D26A"))
    if _p.get("resting_hr"):
        _header_stats.append(("RHR", f"{_p['resting_hr']} bpm", "#4DA6FF"))
    if _p.get("weekly_mileage_km"):
        _header_stats.append(("Weekly", f"{_p['weekly_mileage_km']} km", "#AB47BC"))
    if _p.get("body_battery_current"):
        _bb = _p["body_battery_current"]
        _bb_color = "#00D26A" if _bb >= 50 else "#FF9800" if _bb >= 25 else "#FF5252"
        _header_stats.append(("Battery", str(_bb), _bb_color))

_stat_pills_html = ""
for _label, _val, _color in _header_stats:
    _stat_pills_html += (
        f'<div style="background:{_color}15;border:1px solid {_color}33;border-radius:10px;'
        f'padding:6px 14px;display:flex;align-items:center;gap:6px;">'
        f'<span style="color:{_color}99;font-size:0.75rem;font-weight:500;">{_label}</span>'
        f'<span style="color:{_color};font-weight:700;font-size:0.95rem;">{_val}</span>'
        f'</div>'
    )

# Today's workout pill
_workout_html = ""
if _today_workout:
    _wt = _today_workout.get("workout_type", "")
    _wt_icons = {"easy": "\U0001f7e2", "tempo": "\U0001f7e0", "interval": "\U0001f534", "long_run": "\U0001f535",
                 "recovery": "\U0001f49a", "race": "\U0001f3c1", "rest": "\U0001f634", "speed": "\u26a1", "threshold": "\U0001f7e1"}
    _wt_icon = _wt_icons.get(_wt, "\U0001f3c3")
    _wo_name = _today_workout.get("name", _wt.replace("_", " ").title())
    _completed = _today_workout.get("completed", False)
    if _completed:
        _workout_html = (
            f'<div style="background:#00D26A15;border:1px solid #00D26A33;border-radius:10px;'
            f'padding:6px 14px;display:flex;align-items:center;gap:6px;">'
            f'<span style="font-size:0.85rem;">\u2705</span>'
            f'<span style="color:#00D26A;font-weight:600;font-size:0.85rem;">{_wo_name}</span>'
            f'</div>'
        )
    else:
        _workout_html = (
            f'<div style="background:#FFB80015;border:1px solid #FFB80033;border-radius:10px;'
            f'padding:6px 14px;display:flex;align-items:center;gap:6px;">'
            f'<span style="font-size:0.85rem;">{_wt_icon}</span>'
            f'<span style="color:#FFB800;font-weight:600;font-size:0.85rem;">Today: {_wo_name}</span>'
            f'</div>'
        )
elif any(isinstance(pl, dict) and pl.get("accepted") for pl in (st.session_state.plans or [])):
    _workout_html = (
        '<div style="background:#00D26A15;border:1px solid #00D26A33;border-radius:10px;'
        'padding:6px 14px;display:flex;align-items:center;gap:6px;">'
        '<span style="font-size:0.85rem;">\U0001f634</span>'
        '<span style="color:#69F0AE;font-weight:600;font-size:0.85rem;">Rest day</span>'
        '</div>'
    )

# Greeting based on time of day
from datetime import datetime as _dt_now

_hour = _dt_now.now().hour
_greeting = "Good morning" if _hour < 12 else "Good afternoon" if _hour < 18 else "Good evening"

st.markdown(
    f'<div style="background:linear-gradient(135deg, #1E2128 0%, #252830 100%);'
    f'border:1px solid #2D3139;border-radius:14px;padding:1rem 1.5rem;margin-bottom:1rem;'
    f'display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap;">'
    # Avatar
    f'<div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#00D26A,#00A854);'
    f'display:flex;align-items:center;justify-content:center;color:#fff;'
    f'font-weight:700;font-size:1rem;flex-shrink:0;">{_header_initials}</div>'
    # Greeting + name
    f'<div style="flex:1;min-width:140px;">'
    f'<div style="color:#8B92A5;font-size:0.8rem;">{_greeting}</div>'
    f'<div style="color:#FAFAFA;font-weight:600;font-size:1.15rem;">{_user_display_name}</div>'
    f'</div>'
    # Stats pills
    f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
    f'{_stat_pills_html}'
    f'{_workout_html}'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ── Tabs ─────────────────────────────────────────────────────────────

tab_names = ["🏠 Feed", "Fitness Profile", "Training Plan", "Calendar", "🔥 HYROX", "AI Coach", "User Profile"]
if st.session_state.role == "admin":
    tab_names.append("Admin Panel")

tabs = st.tabs(tab_names)
tab_feed = tabs[0]
tab_profile = tabs[1]
tab_plan = tabs[2]
tab_calendar = tabs[3]
tab_hyrox = tabs[4]
tab_coach = tabs[5]
tab_user_settings = tabs[6]
tab_admin = tabs[7] if st.session_state.role == "admin" else None


# ── Tab 0: Feed ──────────────────────────────────────────────────────

with tab_feed:
    st.markdown('<div class="pf-section-header">Activity Feed</div>', unsafe_allow_html=True)

    try:
        feed_r = requests.get(
            f"{API_BASE}/feed?limit=30&offset=0",
            headers=_auth_headers(), timeout=15,
        )
        feed_events = feed_r.json() if feed_r.status_code == 200 else []
    except requests.ConnectionError:
        feed_events = []
        st.error("Cannot reach API")

    if not feed_events:
        st.markdown(
            '<div style="text-align:center;padding:3rem;color:#8B92A5;">'
            '<div style="font-size:3rem;margin-bottom:1rem;">🏃</div>'
            "<div>No activity yet! Complete a workout or add friends to see their activity here.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        for idx, ev in enumerate(feed_events):
            _event_type_icons = {
                "activity": "🏃", "plan": "📋", "pb": "🏆", "hyrox": "🔥", "milestone": "⭐",
            }
            icon = _event_type_icons.get(ev.get("event_type", ""), "📌")
            user_name = ev.get("user_name", "Unknown")
            initials = "".join(w[0].upper() for w in user_name.split()[:2]) if user_name else "?"
            created = ev.get("created_at", "")[:10]
            like_count = ev.get("like_count", 0)
            comment_count = ev.get("comment_count", 0)
            liked_by_me = ev.get("liked_by_me", False)
            heart = "❤️" if liked_by_me else "🤍"

            st.markdown(
                f'<div style="background:#1E2128;border:1px solid #2D3139;border-radius:12px;'
                f'padding:1.2rem;margin-bottom:0.8rem;">'
                f'<div style="display:flex;align-items:center;gap:0.8rem;margin-bottom:0.6rem;">'
                f'<div style="width:36px;height:36px;border-radius:50%;background:#00D26A33;'
                f'display:flex;align-items:center;justify-content:center;color:#00D26A;'
                f'font-weight:700;font-size:0.85rem;">{initials}</div>'
                f'<div><span style="color:#FAFAFA;font-weight:600;">{user_name}</span>'
                f'<span style="color:#8B92A5;font-size:0.8rem;margin-left:0.5rem;">{created}</span></div>'
                f'</div>'
                f'<div style="font-size:1.05rem;color:#FAFAFA;margin-bottom:0.3rem;">'
                f'{icon} {ev.get("title", "")}</div>'
                + (f'<div style="color:#B0B7C3;font-size:0.9rem;margin-bottom:0.5rem;">{ev.get("body")}</div>'
                   if ev.get("body") else '')
                + f'<div style="color:#8B92A5;font-size:0.85rem;">'
                f'{heart} {like_count}  ·  💬 {comment_count}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Actions row
            col_like, col_comment, col_spacer = st.columns([1, 1, 4])
            with col_like:
                like_label = "Unlike" if liked_by_me else "Like"
                if st.button(f"{heart} {like_label}", key=f"feed_like_{ev['id']}_{idx}", use_container_width=True):
                    try:
                        requests.post(
                            f"{API_BASE}/feed/{ev['id']}/like",
                            headers=_auth_headers(), timeout=10,
                        )
                        st.rerun()
                    except requests.ConnectionError:
                        st.error("Cannot reach API")

            with col_comment:
                if st.button("💬 Comment", key=f"feed_toggle_comment_{ev['id']}_{idx}", use_container_width=True):
                    if st.session_state.get(f"show_comments_{ev['id']}"):
                        st.session_state[f"show_comments_{ev['id']}"] = False
                    else:
                        st.session_state[f"show_comments_{ev['id']}"] = True
                    st.rerun()

            # Comments section (expandable)
            if st.session_state.get(f"show_comments_{ev['id']}"):
                try:
                    comments_r = requests.get(
                        f"{API_BASE}/feed/{ev['id']}/comments",
                        headers=_auth_headers(), timeout=10,
                    )
                    comments = comments_r.json() if comments_r.status_code == 200 else []
                except requests.ConnectionError:
                    comments = []

                for c in comments:
                    c_name = c.get("user_name", "?")
                    c_date = c.get("created_at", "")[:10]
                    st.markdown(
                        f'<div style="margin-left:2rem;padding:0.5rem 0.8rem;border-left:2px solid #2D3139;'
                        f'margin-bottom:0.3rem;">'
                        f'<span style="color:#00D26A;font-weight:600;font-size:0.85rem;">{c_name}</span>'
                        f'<span style="color:#8B92A5;font-size:0.75rem;margin-left:0.4rem;">{c_date}</span>'
                        f'<div style="color:#B0B7C3;font-size:0.9rem;">{c.get("body", "")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                with st.form(key=f"comment_form_{ev['id']}_{idx}", clear_on_submit=True):
                    comment_text = st.text_input("Add a comment", key=f"comment_input_{ev['id']}_{idx}",
                                                  label_visibility="collapsed", placeholder="Write a comment...")
                    if st.form_submit_button("Post", use_container_width=True):
                        if comment_text and comment_text.strip():
                            try:
                                requests.post(
                                    f"{API_BASE}/feed/{ev['id']}/comment",
                                    json={"body": comment_text.strip()},
                                    headers=_auth_headers(), timeout=10,
                                )
                                st.rerun()
                            except requests.ConnectionError:
                                st.error("Cannot reach API")


# ── Tab 1: Performance Profile ───────────────────────────────────────

def _gauge_chart(value, title, range_min, range_max, color, steps, key_suffix):
    """Render a Plotly gauge chart."""
    import plotly.graph_objects as go
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 14, "color": "#8B92A5"}},
        number={"font": {"size": 36, "color": "#FAFAFA"}},
        gauge={
            "axis": {"range": [range_min, range_max], "tickcolor": "#3A3F4B", "tickfont": {"color": "#8B92A5"}},
            "bar": {"color": color},
            "bgcolor": "#2D3139",
            "borderwidth": 0,
            "steps": steps,
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=220, margin=dict(t=35, b=15, l=25, r=25),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"gauge_{key_suffix}")


def _badge(text, color, bg=None):
    """Render an inline badge."""
    if not bg:
        bg = color + "22"
    return (
        f'<span style="background:{bg};color:{color};padding:4px 14px;border-radius:12px;'
        f'font-size:0.85rem;font-weight:600;">{text}</span>'
    )


def _section_card(title, content_html, accent="#2563EB"):
    """Render a section card with accent left border."""
    return (
        f'<div style="background:#1E2028;border-left:3px solid {accent};border-radius:0 10px 10px 0;'
        f'padding:14px 18px;margin-bottom:0.75rem;">'
        f'<div style="font-weight:600;color:{accent};margin-bottom:6px;font-size:0.95rem;">{title}</div>'
        f'<div style="color:#C9CDD5;font-size:0.88rem;line-height:1.6;">{content_html}</div>'
        f'</div>'
    )


def _bullet_list(items, color="#00D26A", icon="▸"):
    """Render a colored bullet list."""
    lines = "".join(
        f'<div style="padding:3px 0;color:#C9CDD5;font-size:0.88rem;">'
        f'<span style="color:{color};margin-right:6px;">{icon}</span>{item}</div>'
        for item in items
    )
    return f'<div style="padding:4px 0;">{lines}</div>'


def _fmt_time(seconds):
    """Format seconds as H:MM:SS or M:SS."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


with tab_profile:
    if st.session_state.garmin_logged_in:
        if st.button("\U0001f504 Sync Profile from Garmin", key="load_profile_btn"):
            with st.spinner("Fetching from Garmin Connect..."):
                r = requests.get(f"{API_BASE}/profile?sync=true", headers=_auth_headers(), timeout=60)
                if r.status_code == 200:
                    st.session_state.profile = r.json()
                    # Clear cached analytics so they get recomputed
                    st.session_state.pop("analytics", None)
                else:
                    st.error("Failed to fetch profile")

    p = st.session_state.profile
    if not p:
        st.info("No profile data yet. Connect to Garmin and sync to load your fitness profile.")
    else:
        # Fetch analytics (cached per session)
        analytics = st.session_state.get("analytics")
        if not analytics:
            try:
                r = requests.get(f"{API_BASE}/profile/analytics", headers=_auth_headers(), timeout=30)
                if r.status_code == 200:
                    analytics = r.json()
                    st.session_state.analytics = analytics
            except Exception:
                pass

        import plotly.graph_objects as go

        # ── Sub-tabs ──
        prof_tabs = st.tabs([
            "📊 Snapshot", "🫀 Aerobic Engine", "🏃 Running Economy",
            "🔋 Load & Recovery", "🏁 Race Predictions",
            "📋 Recommendations", "📈 Trends",
        ])

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 1: ATHLETE SNAPSHOT
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[0]:
            snap = (analytics or {}).get("snapshot", {})
            level = snap.get("fitness_level", "—")
            level_colors = {"Beginner": "#FF9800", "Intermediate": "#2196F3", "Advanced": "#00D26A", "Elite": "#FFD600"}
            level_color = level_colors.get(level, "#8B92A5")

            # Hero card
            vdot_val = snap.get("vdot", "—")
            t_status = snap.get("training_status", "—")
            t_age = snap.get("training_age_estimate", "—")
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1A1D24,#1E2028);border-radius:12px;'
                f'padding:20px 24px;margin-bottom:1rem;border:1px solid #2D3139;">'
                f'<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
                f'<div style="background:{level_color}22;border:2px solid {level_color};border-radius:50%;'
                f'width:64px;height:64px;display:flex;align-items:center;justify-content:center;'
                f'font-size:1.6rem;font-weight:800;color:{level_color};">'
                f'{level[0] if level != "—" else "?"}</div>'
                f'<div>'
                f'<div style="font-size:1.3rem;font-weight:700;color:#FAFAFA;">{level} Athlete</div>'
                f'<div style="color:#8B92A5;font-size:0.85rem;margin-top:2px;">'
                f'Training age: {t_age} · Status: {t_status}</div>'
                f'</div>'
                f'<div style="margin-left:auto;text-align:right;">'
                f'<div style="font-size:2rem;font-weight:800;color:#FFD600;">'
                f'{vdot_val if vdot_val != "—" else "—"}</div>'
                f'<div style="color:#8B92A5;font-size:0.8rem;">VDOT</div>'
                f'</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # 6 KPI metric cards
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                st.markdown(_metric_card("VO2 Max", str(p.get("vo2_max", "—")), "", "green"), unsafe_allow_html=True)
            with r1c2:
                st.markdown(_metric_card("Resting HR", str(p.get("resting_hr", "—")), "bpm", "blue"), unsafe_allow_html=True)
            with r1c3:
                st.markdown(_metric_card("Max HR", str(p.get("max_hr", "—")), "bpm", "red"), unsafe_allow_html=True)

            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                st.markdown(_metric_card("Weekly Mileage", str(p.get("weekly_mileage_km", "—")), "km", "cyan"), unsafe_allow_html=True)
            with r2c2:
                es = p.get("endurance_score")
                st.markdown(_metric_card("Endurance Score", str(es if es else "—"), "", "purple"), unsafe_allow_html=True)
            with r2c3:
                w = p.get("weight_kg")
                fa = p.get("fitness_age")
                label = f'{w} kg' if w else "—"
                if fa:
                    label += f' · Age {fa}'
                st.markdown(_metric_card("Weight / Fitness Age", label, "", "orange"), unsafe_allow_html=True)

            # Strengths vs Weaknesses
            st.markdown("")
            sw_col1, sw_col2 = st.columns(2)
            with sw_col1:
                st.markdown(
                    _section_card("💪 Strengths", _bullet_list(snap.get("strengths", []), "#00D26A", "✓"), "#00D26A"),
                    unsafe_allow_html=True,
                )
            with sw_col2:
                st.markdown(
                    _section_card("⚠️ Weaknesses", _bullet_list(snap.get("weaknesses", []), "#FF9800", "✗"), "#FF9800"),
                    unsafe_allow_html=True,
                )

            # HR Zone distribution
            zones = p.get("hr_zones", [])
            if zones:
                st.markdown("")
                st.markdown('<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin-bottom:6px;">HR Zone Distribution</div>', unsafe_allow_html=True)
                zone_colors = ["#4CAF50", "#8BC34A", "#FFC107", "#FF9800", "#F44336"]
                zone_labels = ["Z1 Recovery", "Z2 Aerobic", "Z3 Tempo", "Z4 Threshold", "Z5 VO2max"]
                zone_html = '<div style="display:flex;gap:4px;border-radius:8px;overflow:hidden;">'
                for i, z in enumerate(zones[:5]):
                    width_pct = max(100 / len(zones), 10)
                    c = zone_colors[i] if i < len(zone_colors) else "#607D8B"
                    lbl = zone_labels[i] if i < len(zone_labels) else f"Z{z.get('zone', i+1)}"
                    zone_html += (
                        f'<div style="flex:1;background:{c}33;padding:8px 6px;text-align:center;">'
                        f'<div style="font-size:0.7rem;color:{c};font-weight:600;">{lbl}</div>'
                        f'<div style="font-size:0.8rem;color:#C9CDD5;">{z.get("low_bpm","")}-{z.get("high_bpm","")}</div>'
                        f'</div>'
                    )
                zone_html += '</div>'
                st.markdown(zone_html, unsafe_allow_html=True)

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 2: AEROBIC ENGINE
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[1]:
            aero = (analytics or {}).get("aerobic", {})

            # VO2max gauge + interpretation
            gc1, gc2 = st.columns(2)
            vo2 = p.get("vo2_max")
            if vo2 and isinstance(vo2, (int, float)):
                with gc1:
                    _gauge_chart(vo2, "VO2 Max", 20, 70, "#00D26A", [
                        {"range": [20, 35], "color": "rgba(244,67,54,0.15)"},
                        {"range": [35, 50], "color": "rgba(255,152,0,0.15)"},
                        {"range": [50, 70], "color": "rgba(0,210,106,0.15)"},
                    ], "vo2_aero")
                with gc2:
                    cat = aero.get("vo2max_category", "—")
                    interp = aero.get("vo2max_interpretation", "")
                    st.markdown(
                        f'<div style="padding-top:20px;">'
                        f'{_badge(cat, "#00D26A" if cat in ("Superior","Excellent") else "#FF9800" if cat in ("Good","Fair") else "#F44336")}'
                        f'<div style="color:#C9CDD5;font-size:0.88rem;margin-top:12px;line-height:1.6;">{interp}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Aerobic vs Anaerobic balance
            aer_r = aero.get("aerobic_ratio", 0)
            ana_r = aero.get("anaerobic_ratio", 0)
            st.markdown("")
            st.markdown('<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin-bottom:6px;">Training Effect Balance</div>', unsafe_allow_html=True)
            aer_pct = round(aer_r * 100)
            ana_pct = round(ana_r * 100)
            st.markdown(
                f'<div style="display:flex;border-radius:8px;overflow:hidden;height:28px;">'
                f'<div style="flex:{aer_pct};background:#2196F3;display:flex;align-items:center;justify-content:center;'
                f'font-size:0.75rem;font-weight:600;color:#fff;">{aer_pct}% Aerobic</div>'
                f'<div style="flex:{ana_pct};background:#F44336;display:flex;align-items:center;justify-content:center;'
                f'font-size:0.75rem;font-weight:600;color:#fff;">{ana_pct}% Anaerobic</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Threshold quality + Cardiac efficiency
            st.markdown("")
            tq_col, ce_col = st.columns(2)
            with tq_col:
                thr_q = aero.get("threshold_quality", "—")
                thr_pct = aero.get("threshold_pct_of_vo2max")
                content = thr_q
                if thr_pct:
                    content += f"<br><span style='color:#8B92A5;font-size:0.8rem;'>LT pace = {thr_pct}% of VDOT pace</span>"
                # LT metrics — normalize speed to m/s
                lt_hr = p.get("lactate_threshold_hr")
                lt_spd = p.get("lactate_threshold_speed")
                # Validate LT speed is in reasonable m/s range (2.5-6.5)
                if lt_spd and lt_spd > 0:
                    if lt_spd < 2.0 and 2.0 <= lt_spd * 10 <= 7.0:
                        lt_spd = lt_spd * 10
                    elif not (2.0 <= lt_spd <= 7.0):
                        lt_spd = None  # unreliable
                if lt_hr or lt_spd:
                    parts = []
                    if lt_hr:
                        parts.append(f"LT HR: {lt_hr:.0f} bpm")
                    if lt_spd and lt_spd > 0:
                        pm, ps = divmod(int(1000 / lt_spd), 60)
                        parts.append(f"LT Pace: {pm}:{ps:02d}/km")
                    content += f"<br><span style='color:#60A5FA;font-size:0.8rem;'>{' · '.join(parts)}</span>"
                st.markdown(_section_card("🎯 Threshold Quality", content, "#FF9800"), unsafe_allow_html=True)
            with ce_col:
                ce = aero.get("cardiac_efficiency", "—")
                drift = aero.get("cardiac_drift_indicator")
                content = ce
                if drift:
                    content += f"<br><span style='color:#8B92A5;font-size:0.8rem;'>HR/Pace ratio: {drift:.3f}</span>"
                decoup = aero.get("aerobic_decoupling_pct")
                if decoup is not None:
                    content += f"<br><span style='color:#8B92A5;font-size:0.8rem;'>Aerobic decoupling: {decoup:+.1f}%</span>"
                st.markdown(_section_card("❤️ Cardiac Efficiency", content, "#F44336"), unsafe_allow_html=True)

            # Pace vs HR scatter
            acts = p.get("recent_activities", [])
            scatter_data = [(a["avg_pace_sec_per_km"], a["avg_hr"]) for a in acts
                           if a.get("avg_pace_sec_per_km") and a.get("avg_hr")]
            if scatter_data:
                st.markdown("")
                paces_v, hrs_v = zip(*scatter_data, strict=False)
                # Format paces as MM:SS for display
                pace_labels = [f"{int(pv)//60}:{int(pv)%60:02d}" for pv in paces_v]
                fig_scatter = go.Figure()
                fig_scatter.add_trace(go.Scatter(
                    x=[pv / 60 for pv in paces_v], y=list(hrs_v),
                    mode="markers",
                    marker=dict(color="#2196F3", size=8, opacity=0.7),
                    customdata=pace_labels,
                    hovertemplate="Pace: %{customdata}/km<br>HR: %{y} bpm<extra></extra>",
                ))
                # Build MM:SS tick labels for the x-axis
                pace_min = min(paces_v) / 60
                pace_max = max(paces_v) / 60
                import math
                tick_start = math.floor(pace_min)
                tick_end = math.ceil(pace_max)
                tick_vals = []
                tick_text = []
                for m in range(tick_start, tick_end + 1):
                    for s in (0, 30):
                        val = m + s / 60
                        if pace_min - 0.5 <= val <= pace_max + 0.5:
                            tick_vals.append(val)
                            tick_text.append(f"{m}:{s:02d}")
                fig_scatter.update_layout(
                    title="Cardiac Efficiency: Pace vs Heart Rate",
                    xaxis_title="Pace (min/km)", yaxis_title="Avg HR (bpm)",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C9CDD4", size=11),
                    margin=dict(l=50, r=20, t=40, b=40), height=300,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", autorange="reversed",
                               tickvals=tick_vals, ticktext=tick_text),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                )
                st.plotly_chart(fig_scatter, use_container_width=True, key="scatter_pace_hr")

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 3: RUNNING ECONOMY
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[2]:
            econ = (analytics or {}).get("economy", {})
            grade = econ.get("overall_grade", "—")
            grade_colors = {"A": "#00D26A", "B": "#2196F3", "C": "#FF9800", "D": "#F44336", "—": "#8B92A5"}
            gc = grade_colors.get(grade, "#8B92A5")

            # Grade badge
            st.markdown(
                f'<div style="text-align:center;margin-bottom:1rem;">'
                f'<div style="display:inline-block;background:{gc}22;border:2px solid {gc};border-radius:16px;'
                f'padding:12px 28px;">'
                f'<div style="font-size:2rem;font-weight:800;color:{gc};">{grade}</div>'
                f'<div style="font-size:0.8rem;color:#8B92A5;">Running Economy Grade</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # 4 metric cards
            ec1, ec2, ec3, ec4 = st.columns(4)
            cad = econ.get("cadence_avg")
            with ec1:
                val = f"{cad:.0f}" if cad else "—"
                st.markdown(_metric_card("Cadence", val, "spm", "cyan"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B92A5;">{econ.get("cadence_grade","")}</div>', unsafe_allow_html=True)
            with ec2:
                sl = econ.get("stride_length_avg")
                val = f"{sl:.2f}" if sl else "—"
                st.markdown(_metric_card("Stride Length", val, "m", "blue"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B92A5;">{econ.get("stride_grade","")}</div>', unsafe_allow_html=True)
            with ec3:
                gct = econ.get("gct_avg")
                val = f"{gct:.0f}" if gct else "—"
                st.markdown(_metric_card("Ground Contact", val, "ms", "orange"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B92A5;">{econ.get("gct_grade","")}</div>', unsafe_allow_html=True)
            with ec4:
                vo = econ.get("vert_osc_avg")
                val = f"{vo:.1f}" if vo else "—"
                st.markdown(_metric_card("Vert. Oscillation", val, "cm", "purple"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B92A5;">{econ.get("vert_osc_grade","")}</div>', unsafe_allow_html=True)

            # Inefficiency callouts
            ineff = econ.get("inefficiencies", [])
            if ineff:
                st.markdown("")
                st.markdown(
                    _section_card("🔧 Key Inefficiencies", _bullet_list(ineff, "#FF9800", "⚠"), "#FF9800"),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown("")
                st.markdown(
                    _section_card("✅ Running Mechanics", "No significant inefficiencies detected. Mechanics look solid.", "#00D26A"),
                    unsafe_allow_html=True,
                )

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 4: LOAD & RECOVERY
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[3]:
            lr = (analytics or {}).get("load_recovery", {})

            # Top row: Body Battery + Sleep Score + Stress
            lr1, lr2, lr3 = st.columns(3)
            with lr1:
                bb = p.get("body_battery_current")
                if bb and isinstance(bb, (int, float)):
                    _gauge_chart(bb, "Body Battery", 0, 100, "#00D26A", [
                        {"range": [0, 25], "color": "rgba(244,67,54,0.15)"},
                        {"range": [25, 60], "color": "rgba(255,152,0,0.15)"},
                        {"range": [60, 100], "color": "rgba(0,210,106,0.15)"},
                    ], "body_battery")
                else:
                    st.markdown(_metric_card("Body Battery", "—", "", "green"), unsafe_allow_html=True)
            with lr2:
                ss = p.get("sleep_score")
                if ss and isinstance(ss, (int, float)):
                    _gauge_chart(ss, "Sleep Score", 0, 100, "#AB47BC", [
                        {"range": [0, 40], "color": "rgba(244,67,54,0.15)"},
                        {"range": [40, 70], "color": "rgba(255,152,0,0.15)"},
                        {"range": [70, 100], "color": "rgba(0,210,106,0.15)"},
                    ], "sleep_score")
                else:
                    st.markdown(_metric_card("Sleep Score", "—", "", "purple"), unsafe_allow_html=True)
            with lr3:
                sa = p.get("stress_avg")
                if sa and isinstance(sa, (int, float)):
                    stress_color = "#00D26A" if sa <= 25 else "#FF9800" if sa <= 50 else "#F44336"
                    _gauge_chart(sa, "Avg Stress", 0, 100, stress_color, [
                        {"range": [0, 25], "color": "rgba(0,210,106,0.15)"},
                        {"range": [25, 50], "color": "rgba(255,152,0,0.15)"},
                        {"range": [50, 100], "color": "rgba(244,67,54,0.15)"},
                    ], "stress_avg")
                else:
                    st.markdown(_metric_card("Avg Stress", "—", "", "orange"), unsafe_allow_html=True)

            # Sleep breakdown pie
            sleep_dur = p.get("sleep_duration_seconds")
            sleep_deep = p.get("sleep_deep_seconds")
            sleep_light = p.get("sleep_light_seconds")
            sleep_rem = p.get("sleep_rem_seconds")
            sleep_awake = p.get("sleep_awake_seconds")

            lr_col1, lr_col2 = st.columns(2)
            with lr_col1:
                if sleep_dur and any([sleep_deep, sleep_light, sleep_rem]):
                    labels, vals, colors = [], [], []
                    if sleep_deep:
                        labels.append("Deep"); vals.append(sleep_deep / 60); colors.append("#1565C0")
                    if sleep_light:
                        labels.append("Light"); vals.append(sleep_light / 60); colors.append("#42A5F5")
                    if sleep_rem:
                        labels.append("REM"); vals.append(sleep_rem / 60); colors.append("#AB47BC")
                    if sleep_awake:
                        labels.append("Awake"); vals.append(sleep_awake / 60); colors.append("#FF9800")
                    fig_sleep = go.Figure(go.Pie(
                        labels=labels, values=vals, marker_colors=colors,
                        hole=0.55, textinfo="label+percent", textfont_size=11,
                        textfont_color="#C9CDD5",
                    ))
                    fig_sleep.update_layout(
                        title=f"Sleep Stages ({sleep_dur / 3600:.1f}h total)",
                        title_font=dict(size=13, color="#8B92A5"),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        height=280, margin=dict(t=40, b=20, l=20, r=20),
                        legend=dict(font=dict(color="#8B92A5", size=10)),
                        showlegend=True,
                    )
                    st.plotly_chart(fig_sleep, use_container_width=True, key="sleep_pie")
                else:
                    st.markdown(_section_card("😴 Sleep", "No sleep stage data available", "#AB47BC"), unsafe_allow_html=True)

            with lr_col2:
                # Load + HRV + Fatigue
                load_status = lr.get("load_status", "—")
                load_colors = {"Optimal": "#00D26A", "Recovery": "#2196F3", "Overreaching": "#F44336",
                               "Undertraining": "#FF9800", "Unknown": "#8B92A5"}
                lc = load_colors.get(load_status, "#8B92A5")
                tl = lr.get("training_load_7day")
                lf = lr.get("load_focus")
                load_html = f'{_badge(load_status, lc)}'
                if tl:
                    load_html += f'<div style="color:#C9CDD5;font-size:0.85rem;margin-top:8px;">7-day load: {tl:.0f}</div>'
                if lf:
                    load_html += f'<div style="color:#8B92A5;font-size:0.8rem;">Focus: {lf}</div>'
                st.markdown(_section_card("📊 Training Load", load_html, lc), unsafe_allow_html=True)

                hrv_a = lr.get("hrv_assessment", "—")
                hrv_c = {"Stable": "#00D26A", "Improving": "#2196F3", "Declining": "#F44336"}.get(hrv_a, "#8B92A5")
                hrv_html = f'{_badge(hrv_a, hrv_c)}'
                hlv = p.get("hrv_last_night")
                if hlv:
                    hrv_html += f'<span style="color:#C9CDD5;font-size:0.85rem;margin-left:10px;">Last night: {hlv:.0f} ms</span>'
                st.markdown(_section_card("💓 HRV Status", hrv_html, hrv_c), unsafe_allow_html=True)

                fatigue = lr.get("fatigue_risk", "—")
                fat_c = {"Low": "#00D26A", "Moderate": "#FF9800", "High": "#F44336"}.get(fatigue, "#8B92A5")
                st.markdown(_section_card("⚡ Fatigue Risk", _badge(fatigue, fat_c), fat_c), unsafe_allow_html=True)

            # Recovery tips
            tips = lr.get("recovery_tips", [])
            if tips:
                st.markdown("")
                st.markdown(
                    _section_card("💤 Recovery Tips", _bullet_list(tips, "#AB47BC", "→"), "#AB47BC"),
                    unsafe_allow_html=True,
                )

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 5: RACE PREDICTIONS
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[4]:
            rp = (analytics or {}).get("race_predictions", {})
            rp_vdot = rp.get("vdot")
            preds = rp.get("predictions", [])

            if rp_vdot:
                # Check if Garmin predictions are available
                garmin_count = sum(1 for pred in preds if pred.get("confidence") == "High")
                source_note = ""
                if garmin_count:
                    source_note = f'<span style="color:#00D26A;font-size:0.8rem;margin-left:8px;">({garmin_count} from Garmin)</span>'
                st.markdown(
                    f'<div style="text-align:center;margin-bottom:1rem;">'
                    f'<span style="font-size:0.85rem;color:#8B92A5;">Based on </span>'
                    f'<span style="font-size:1.1rem;font-weight:700;color:#FFD600;">VDOT {rp_vdot}</span>'
                    f'{source_note}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Predictions table
            if preds:
                table_html = (
                    '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;margin-bottom:1rem;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #2D3139;">'
                    '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.8rem;">Distance</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.8rem;">Predicted Time</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.8rem;">Pace/km</th>'
                    '<th style="text-align:right;padding:8px;color:#8B92A5;font-size:0.8rem;">Confidence</th>'
                    '</tr>'
                )
                for pred in preds:
                    time_str = _fmt_time(pred["predicted_seconds"])
                    pm, ps = divmod(int(pred["pace_sec_per_km"]), 60)
                    pace_str = f"{pm}:{ps:02d}"
                    conf = pred["confidence"]
                    conf_c = {"High": "#00D26A", "Moderate": "#FF9800", "Low": "#F44336"}.get(conf, "#8B92A5")
                    table_html += (
                        f'<tr style="border-bottom:1px solid #2D313922;">'
                        f'<td style="padding:10px 8px;font-weight:500;color:#FAFAFA;">{pred["distance"]}</td>'
                        f'<td style="padding:10px 8px;text-align:center;color:#00D26A;font-weight:600;font-size:1.05rem;">{time_str}</td>'
                        f'<td style="padding:10px 8px;text-align:center;color:#C9CDD5;">{pace_str}/km</td>'
                        f'<td style="padding:10px 8px;text-align:right;">{_badge(conf, conf_c)}</td>'
                        f'</tr>'
                    )
                table_html += '</table></div>'
                st.markdown(table_html, unsafe_allow_html=True)

            # PBs vs Predictions comparison
            pbs = {pr["distance"]: pr["time_seconds"] for pr in p.get("personal_records", [])}
            garmin_preds = {rpp["distance"]: rpp["predicted_seconds"] for rpp in p.get("race_predictions", [])}
            if pbs or garmin_preds:
                st.markdown('<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin:8px 0;">Performance Comparison</div>', unsafe_allow_html=True)
                comp_html = '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;">'
                for pred in preds:
                    dist_key_map = {"Half Marathon": "HALF_MARATHON", "Marathon": "MARATHON", "5K": "5K", "10K": "10K"}
                    nk = dist_key_map.get(pred["distance"], pred["distance"])
                    pb_t = pbs.get(nk)
                    gp_t = garmin_preds.get(nk)
                    if pb_t or gp_t:
                        comp_html += '<div style="padding:6px 0;border-bottom:1px solid #2D313933;">'
                        comp_html += f'<span style="color:#FAFAFA;font-weight:500;width:120px;display:inline-block;">{pred["distance"]}</span>'
                        comp_html += f'<span style="color:#FFD600;margin-right:16px;">VDOT: {_fmt_time(pred["predicted_seconds"])}</span>'
                        if gp_t:
                            comp_html += f'<span style="color:#2196F3;margin-right:16px;">Garmin: {_fmt_time(gp_t)}</span>'
                        if pb_t:
                            comp_html += f'<span style="color:#00D26A;">PB: {_fmt_time(pb_t)}</span>'
                        comp_html += '</div>'
                comp_html += '</div>'
                st.markdown(comp_html, unsafe_allow_html=True)

            # Fatigue resistance + bias + optimal distance
            st.markdown("")
            rp_c1, rp_c2, rp_c3 = st.columns(3)
            with rp_c1:
                fr = rp.get("fatigue_resistance", 0)
                st.markdown(_metric_card("Fatigue Resistance", f"{fr:.3f}" if fr else "—", "M/5K ratio", "cyan"), unsafe_allow_html=True)
            with rp_c2:
                bias = rp.get("distance_bias", "—")
                st.markdown(_metric_card("Distance Bias", bias, "", "blue"), unsafe_allow_html=True)
            with rp_c3:
                opt = rp.get("optimal_distance", "—")
                st.markdown(_metric_card("Optimal Distance", opt, "", "green"), unsafe_allow_html=True)

            # Consistency notes
            notes = rp.get("consistency_notes", [])
            if notes:
                st.markdown("")
                st.markdown(
                    _section_card("🔍 Consistency Check", _bullet_list(notes, "#FFD600", "→"), "#FFD600"),
                    unsafe_allow_html=True,
                )

            # Fatigue resistance curve chart
            if len(preds) >= 3:
                st.markdown("")
                fig_fr = go.Figure()
                dist_labels = [p_item["distance"] for p_item in preds]
                pace_vals = [p_item["pace_sec_per_km"] / 60 for p_item in preds]
                fig_fr.add_trace(go.Scatter(
                    x=dist_labels, y=pace_vals,
                    mode="lines+markers",
                    line=dict(color="#FF9800", width=3),
                    marker=dict(size=10, color="#FF9800"),
                    fill="tozeroy", fillcolor="rgba(255,152,0,0.1)",
                    hovertemplate="%{x}<br>%{y:.2f} min/km<extra></extra>",
                ))
                fig_fr.update_layout(
                    title="Fatigue Resistance Curve (Pace vs Distance)",
                    yaxis_title="Pace (min/km)", yaxis_autorange="reversed",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C9CDD4", size=11),
                    margin=dict(l=50, r=20, t=40, b=40), height=300,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                )
                st.plotly_chart(fig_fr, use_container_width=True, key="fatigue_curve")

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 6: TRAINING RECOMMENDATIONS
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[5]:
            rec = (analytics or {}).get("recommendations", {})

            # Training split pie
            split = rec.get("split_pct", {})
            if split:
                rc1, rc2 = st.columns([1, 1])
                with rc1:
                    sp_labels = [k.replace("_", " ").title() for k in split]
                    sp_vals = list(split.values())
                    sp_colors = ["#2196F3", "#FF9800", "#F44336", "#AB47BC"]
                    fig_split = go.Figure(go.Pie(
                        labels=sp_labels, values=sp_vals,
                        marker_colors=sp_colors[:len(sp_vals)],
                        hole=0.5, textinfo="label+percent", textfont_size=11,
                        textfont_color="#C9CDD5",
                    ))
                    fig_split.update_layout(
                        title="Recommended Training Split",
                        title_font=dict(size=13, color="#8B92A5"),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        height=280, margin=dict(t=40, b=10, l=10, r=10),
                        legend=dict(font=dict(color="#8B92A5", size=10)),
                    )
                    st.plotly_chart(fig_split, use_container_width=True, key="training_split")

                with rc2:
                    # HYROX progression
                    hyrox_prog = rec.get("hyrox_progression", [])
                    if hyrox_prog:
                        st.markdown(
                            _section_card("🔥 HYROX Progression", _bullet_list(hyrox_prog, "#FF9800", "→"), "#FF9800"),
                            unsafe_allow_html=True,
                        )
                    # Recovery optimization
                    rec_opt = rec.get("recovery_optimization", [])
                    if rec_opt:
                        st.markdown(
                            _section_card("💤 Recovery Optimization", _bullet_list(rec_opt, "#AB47BC", "→"), "#AB47BC"),
                            unsafe_allow_html=True,
                        )

            # Key sessions table
            sessions = rec.get("key_sessions", [])
            if sessions:
                st.markdown("")
                st.markdown('<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin-bottom:6px;">Key Sessions</div>', unsafe_allow_html=True)
                sess_html = (
                    '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #2D3139;">'
                    '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.78rem;">Session</th>'
                    '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.78rem;">Description</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Pace</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">HR</th>'
                    '</tr>'
                )
                session_colors = ["#F44336", "#FF9800", "#2196F3", "#AB47BC", "#00D26A"]
                for i, s in enumerate(sessions):
                    sc = session_colors[i % len(session_colors)]
                    sess_html += (
                        f'<tr style="border-bottom:1px solid #2D313922;">'
                        f'<td style="padding:8px;color:{sc};font-weight:600;font-size:0.88rem;">{s["name"]}</td>'
                        f'<td style="padding:8px;color:#C9CDD5;font-size:0.85rem;">{s["description"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FFD600;font-size:0.85rem;">{s["pace_target"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FF6B6B;font-size:0.85rem;">{s["hr_target"]}</td>'
                        f'</tr>'
                    )
                sess_html += '</table></div>'
                st.markdown(sess_html, unsafe_allow_html=True)

            # Progress benchmarks table
            benchmarks = rec.get("benchmarks", [])
            if benchmarks:
                st.markdown("")
                st.markdown('<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin-bottom:6px;">Progress Benchmarks</div>', unsafe_allow_html=True)
                bench_html = (
                    '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #2D3139;">'
                    '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.78rem;">Metric</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Current</th>'
                    '<th style="text-align:center;padding:8px;color:#2196F3;font-size:0.78rem;">4 Weeks</th>'
                    '<th style="text-align:center;padding:8px;color:#FF9800;font-size:0.78rem;">8 Weeks</th>'
                    '<th style="text-align:center;padding:8px;color:#00D26A;font-size:0.78rem;">12 Weeks</th>'
                    '</tr>'
                )
                for b in benchmarks:
                    bench_html += (
                        f'<tr style="border-bottom:1px solid #2D313922;">'
                        f'<td style="padding:8px;color:#FAFAFA;font-weight:500;">{b["metric"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#C9CDD5;">{b["current"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#2196F3;">{b["target_4wk"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FF9800;">{b["target_8wk"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#00D26A;">{b["target_12wk"]}</td>'
                        f'</tr>'
                    )
                bench_html += '</table></div>'
                st.markdown(bench_html, unsafe_allow_html=True)

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 7: TRENDS
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[6]:
            acts = p.get("recent_activities", [])
            if acts and len(acts) >= 2:
                sorted_acts = sorted(acts, key=lambda a: a.get("start_time", ""))
                dates = [a.get("start_time", "")[:10] for a in sorted_acts]

                chart_layout = dict(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C9CDD4", size=11),
                    margin=dict(l=40, r=20, t=30, b=30),
                    height=250,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                )

                trend_col1, trend_col2 = st.columns(2)

                paces_list = [a.get("avg_pace_sec_per_km") for a in sorted_acts]
                if any(pv is not None for pv in paces_list):
                    with trend_col1:
                        pace_vals, pace_dates, pace_labels_t = [], [], []
                        for d, pv in zip(dates, paces_list, strict=False):
                            if pv and pv > 0:
                                pace_vals.append(pv / 60)
                                pace_dates.append(d)
                                pace_labels_t.append(f"{int(pv)//60}:{int(pv)%60:02d}")
                        fig_pace = go.Figure()
                        fig_pace.add_trace(go.Scatter(
                            x=pace_dates, y=pace_vals,
                            mode="lines+markers",
                            line=dict(color="#00D26A", width=2), marker=dict(size=5),
                            customdata=pace_labels_t,
                            hovertemplate="%%{x}<br>%%{customdata}/km<extra></extra>",
                        ))
                        import math as _math
                        _pmin_t = min(pace_vals)
                        _pmax_t = max(pace_vals)
                        _tvs, _tts = [], []
                        for _m in range(int(_math.floor(_pmin_t)), int(_math.ceil(_pmax_t)) + 1):
                            for _s in (0, 30):
                                _v = _m + _s / 60
                                if _pmin_t - 0.5 <= _v <= _pmax_t + 0.5:
                                    _tvs.append(_v)
                                    _tts.append(f"{_m}:{_s:02d}")
                        fig_pace.update_layout(
                            title="Average Pace", yaxis_title="min/km",
                            yaxis_autorange="reversed",
                            yaxis_tickvals=_tvs, yaxis_ticktext=_tts,
                            **chart_layout,
                        )
                        st.plotly_chart(fig_pace, use_container_width=True, key="trend_pace")

                hr_list = [a.get("avg_hr") for a in sorted_acts]
                if any(h is not None for h in hr_list):
                    with trend_col2:
                        hr_vals, hr_dates = [], []
                        for d, hv in zip(dates, hr_list, strict=False):
                            if hv and hv > 0:
                                hr_vals.append(hv)
                                hr_dates.append(d)
                        fig_hr = go.Figure()
                        fig_hr.add_trace(go.Scatter(
                            x=hr_dates, y=hr_vals,
                            mode="lines+markers",
                            line=dict(color="#FF6B6B", width=2), marker=dict(size=5),
                            hovertemplate="%%{x}<br>%%{y} bpm<extra></extra>",
                        ))
                        fig_hr.update_layout(title="Average Heart Rate", yaxis_title="bpm", **chart_layout)
                        st.plotly_chart(fig_hr, use_container_width=True, key="trend_hr")

                trend_col3, trend_col4 = st.columns(2)

                cadence_list = [a.get("avg_running_cadence") for a in sorted_acts]
                if any(cv is not None for cv in cadence_list):
                    with trend_col3:
                        cad_vals, cad_dates = [], []
                        for d, cv in zip(dates, cadence_list, strict=False):
                            if cv and cv > 0:
                                cad_vals.append(cv)
                                cad_dates.append(d)
                        fig_cad = go.Figure()
                        fig_cad.add_trace(go.Scatter(
                            x=cad_dates, y=cad_vals,
                            mode="lines+markers",
                            line=dict(color="#4ECDC4", width=2), marker=dict(size=5),
                            hovertemplate="%%{x}<br>%%{y:.0f} spm<extra></extra>",
                        ))
                        fig_cad.update_layout(title="Running Cadence", yaxis_title="spm", **chart_layout)
                        st.plotly_chart(fig_cad, use_container_width=True, key="trend_cadence")

                vo2_list = [a.get("vo2_max_value") for a in sorted_acts]
                if any(v is not None for v in vo2_list):
                    with trend_col4:
                        vo2_vals, vo2_dates = [], []
                        for d, vv in zip(dates, vo2_list, strict=False):
                            if vv and vv > 0:
                                vo2_vals.append(vv)
                                vo2_dates.append(d)
                        fig_vo2t = go.Figure()
                        fig_vo2t.add_trace(go.Scatter(
                            x=vo2_dates, y=vo2_vals,
                            mode="lines+markers",
                            line=dict(color="#FFE66D", width=2), marker=dict(size=5),
                            hovertemplate="%%{x}<br>%%{y:.1f}<extra></extra>",
                        ))
                        fig_vo2t.update_layout(title="VO2 Max Trend", yaxis_title="VO2 Max", **chart_layout)
                        st.plotly_chart(fig_vo2t, use_container_width=True, key="trend_vo2")

                # Additional trends: Training Effect + Distance
                trend_col5, trend_col6 = st.columns(2)

                te_aer = [a.get("training_effect_aerobic") for a in sorted_acts]
                te_ana = [a.get("training_effect_anaerobic") for a in sorted_acts]
                if any(t is not None for t in te_aer):
                    with trend_col5:
                        fig_te = go.Figure()
                        ta_vals, ta_dates = [], []
                        tn_vals, tn_dates = [], []
                        for i, (d, av, nv) in enumerate(zip(dates, te_aer, te_ana, strict=False)):
                            if av:
                                ta_vals.append(av); ta_dates.append(d)
                            if nv:
                                tn_vals.append(nv); tn_dates.append(d)
                        if ta_vals:
                            fig_te.add_trace(go.Scatter(
                                x=ta_dates, y=ta_vals, name="Aerobic",
                                mode="lines+markers",
                                line=dict(color="#2196F3", width=2), marker=dict(size=4),
                            ))
                        if tn_vals:
                            fig_te.add_trace(go.Scatter(
                                x=tn_dates, y=tn_vals, name="Anaerobic",
                                mode="lines+markers",
                                line=dict(color="#F44336", width=2), marker=dict(size=4),
                            ))
                        fig_te.update_layout(title="Training Effect", yaxis_title="TE", **chart_layout)
                        st.plotly_chart(fig_te, use_container_width=True, key="trend_te")

                dist_list = [a.get("distance_meters") for a in sorted_acts]
                if any(d is not None for d in dist_list):
                    with trend_col6:
                        d_vals, d_dates = [], []
                        for d, dv in zip(dates, dist_list, strict=False):
                            if dv and dv > 0:
                                d_vals.append(dv / 1000)
                                d_dates.append(d)
                        fig_dist = go.Figure()
                        fig_dist.add_trace(go.Bar(
                            x=d_dates, y=d_vals,
                            marker_color="#AB47BC",
                            hovertemplate="%%{x}<br>%%{y:.1f} km<extra></extra>",
                        ))
                        fig_dist.update_layout(title="Run Distance", yaxis_title="km", **chart_layout)
                        st.plotly_chart(fig_dist, use_container_width=True, key="trend_distance")
            else:
                st.info("Need at least 2 activities to show trends. Sync your Garmin data.")


# ── Tab 2: Training Plan ─────────────────────────────────────────────

with tab_plan:
    has_plan = len(st.session_state.plans) > 0
    has_profile = st.session_state.profile is not None or st.session_state.garmin_logged_in

    # ── Plan Wizard state ────────────────────────────────────────────
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1
    if "wizard_data" not in st.session_state:
        st.session_state.wizard_data = {}

    ALL_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    DAY_LABELS = {d: d.capitalize() for d in ALL_DAYS}

    GOAL_INFO = {
        "5K": {"icon": "⚡", "desc": "Speed-focused plan with VO2max intervals and short speed work. Great for building a fast base.", "weeks": "8-12 weeks"},
        "10K": {"icon": "🔥", "desc": "Balanced plan mixing threshold runs with VO2max work. Builds both speed and endurance.", "weeks": "10-14 weeks"},
        "HALF_MARATHON": {"icon": "🏃", "desc": "Endurance plan with progressive long runs up to 22km and tempo sessions.", "weeks": "12-16 weeks"},
        "MARATHON": {"icon": "🏅", "desc": "Full endurance program building to 35km long runs with race-pace specifics.", "weeks": "14-20 weeks"},
        "HYROX": {"icon": "💪", "desc": "Hybrid running + functional fitness plan simulating Hyrox race format.", "weeks": "10-14 weeks"},
    }

    with st.expander("🧭 Plan Builder" if has_plan else "🧭 Create Your Training Plan", expanded=not has_plan):
        step = st.session_state.wizard_step
        wd = st.session_state.wizard_data

        # Progress indicator
        step_labels = ["Goal", "Timeline", "Schedule", "Experience", "Review"]
        progress_html = '<div style="display:flex;gap:4px;margin-bottom:1.2rem;">'
        for i, label in enumerate(step_labels, 1):
            if i < step:
                bg, fg = "#00D26A", "#fff"
            elif i == step:
                bg, fg = "#2563EB", "#fff"
            else:
                bg, fg = "#2A2D35", "#8B92A5"
            progress_html += (
                f'<div style="flex:1;text-align:center;padding:6px 0;background:{bg};'
                f'color:{fg};border-radius:6px;font-size:0.75rem;font-weight:600;">'
                f'{i}. {label}</div>'
            )
        progress_html += '</div>'
        st.markdown(progress_html, unsafe_allow_html=True)

        # ── Step 1: Goal ─────────────────────────────────────────────
        if step == 1:
            st.markdown(
                '<p style="font-size:1rem;color:#C9CDD5;margin-bottom:0.5rem;">'
                'What race are you training for? This determines the plan structure, '
                'workout types, and volume progression.</p>',
                unsafe_allow_html=True,
            )
            cols = st.columns(len(GOAL_INFO))
            for i, (goal_key, info) in enumerate(GOAL_INFO.items()):
                with cols[i]:
                    selected = wd.get("goal_type") == goal_key
                    border = "2px solid #00D26A" if selected else "1px solid #2A2D35"
                    st.markdown(
                        f'<div style="border:{border};border-radius:10px;padding:12px;text-align:center;min-height:120px;">'
                        f'<div style="font-size:1.5rem;">{info["icon"]}</div>'
                        f'<div style="font-weight:700;margin:4px 0;">{goal_key.replace("_"," ")}</div>'
                        f'<div style="font-size:0.7rem;color:#8B92A5;">{info["weeks"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("Select", key=f"goal_{goal_key}", use_container_width=True):
                        wd["goal_type"] = goal_key
                        st.session_state.wizard_step = 2
                        st.rerun()

            if wd.get("goal_type"):
                info = GOAL_INFO[wd["goal_type"]]
                st.info(f'{info["icon"]} **{wd["goal_type"].replace("_"," ")}** — {info["desc"]}')

        # ── Step 2: Timeline ─────────────────────────────────────────
        elif step == 2:
            st.markdown(
                '<p style="font-size:1rem;color:#C9CDD5;margin-bottom:0.5rem;">'
                'When is your race, and when do you want to start training? '
                'The plan will automatically periodize phases (Base → Build → Peak → Taper) '
                'across the available weeks.</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                target_date = st.date_input(
                    "🏁 Race Date",
                    value=wd.get("target_date", date.today() + timedelta(weeks=14)),
                    min_value=date.today() + timedelta(weeks=6),
                    key="wiz_race_date",
                )
            with col2:
                default_start = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
                start_date = st.date_input(
                    "📅 Plan Start Date",
                    value=wd.get("start_date", default_start),
                    min_value=date.today(),
                    max_value=target_date - timedelta(weeks=4),
                    key="wiz_start_date",
                )
            weeks_avail = (target_date - start_date).days // 7
            st.markdown(
                f'<p style="color:#00D26A;font-weight:600;">📐 {weeks_avail} weeks of training available</p>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<p style="font-size:1rem;color:#C9CDD5;margin-top:1rem;">'
                'Do you have a target finish time? This helps calculate your training paces using '
                'the VDOT system (Jack Daniels\' Running Formula). Leave at 0 if unsure — '
                'we\'ll estimate from your fitness data.</p>',
                unsafe_allow_html=True,
            )
            tc1, tc2 = st.columns(2)
            with tc1:
                target_h = st.number_input("Hours", 0, 6, wd.get("target_h", 0), key="wiz_target_h")
            with tc2:
                target_m = st.number_input("Minutes", 0, 59, wd.get("target_m", 0), key="wiz_target_m")

            nav1, nav2 = st.columns(2)
            with nav1:
                if st.button("← Back", use_container_width=True, key="wiz_back_2"):
                    st.session_state.wizard_step = 1
                    st.rerun()
            with nav2:
                if st.button("Next →", type="primary", use_container_width=True, key="wiz_next_2"):
                    wd["target_date"] = target_date
                    wd["start_date"] = start_date
                    wd["target_h"] = target_h
                    wd["target_m"] = target_m
                    st.session_state.wizard_step = 3
                    st.rerun()

        # ── Step 3: Schedule ─────────────────────────────────────────
        elif step == 3:
            st.markdown(
                '<p style="font-size:1rem;color:#C9CDD5;margin-bottom:0.5rem;">'
                'Which days can you train? Select at least 3. The plan places quality sessions '
                '(intervals, tempo) on non-consecutive days and schedules easy runs around them. '
                'Your long run goes on the day you choose below.</p>',
                unsafe_allow_html=True,
            )
            training_days = st.multiselect(
                "Training Days",
                options=ALL_DAYS,
                default=wd.get("training_days", ["tuesday", "wednesday", "thursday", "saturday", "sunday"]),
                format_func=lambda d: DAY_LABELS[d],
                key="wiz_training_days",
            )
            if len(training_days) < 3:
                st.warning("Select at least 3 training days for an effective plan.")

            long_run_day = st.selectbox(
                "🏃‍♂️ Long Run Day",
                options=ALL_DAYS,
                index=ALL_DAYS.index(wd.get("long_run_day", "sunday")),
                format_func=lambda d: DAY_LABELS[d],
                key="wiz_long_run",
                help="The long run is the cornerstone of endurance training. Pick a day where you have the most time.",
            )

            nav1, nav2 = st.columns(2)
            with nav1:
                if st.button("← Back", use_container_width=True, key="wiz_back_3"):
                    st.session_state.wizard_step = 2
                    st.rerun()
            with nav2:
                if st.button("Next →", type="primary", use_container_width=True, key="wiz_next_3") and len(training_days) >= 3:
                    wd["training_days"] = training_days
                    wd["long_run_day"] = long_run_day
                    st.session_state.wizard_step = 4
                    st.rerun()

        # ── Step 4: Experience ───────────────────────────────────────
        elif step == 4:
            st.markdown(
                '<p style="font-size:1rem;color:#C9CDD5;margin-bottom:0.5rem;">'
                'What is your running experience? This affects training volume and intensity:</p>',
                unsafe_allow_html=True,
            )
            exp_info = {
                "beginner": ("🌱", "Running for less than a year or first-time racer. Lower volume, gentler progression, more recovery."),
                "intermediate": ("📈", "1-3 years of consistent running with some race experience. Moderate volume with structured quality sessions."),
                "advanced": ("🏆", "3+ years of structured training with multiple race finishes. Higher volume, aggressive periodization."),
            }
            for level, (icon, desc) in exp_info.items():
                selected = wd.get("experience") == level
                border = "2px solid #00D26A" if selected else "1px solid #2A2D35"
                st.markdown(
                    f'<div style="border:{border};border-radius:10px;padding:12px 16px;margin-bottom:8px;">'
                    f'<span style="font-size:1.2rem;">{icon}</span> '
                    f'<strong>{level.capitalize()}</strong>'
                    f'<span style="color:#8B92A5;font-size:0.85rem;margin-left:8px;">{desc}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Select {level.capitalize()}", key=f"exp_{level}", use_container_width=True):
                    wd["experience"] = level
                    st.session_state.wizard_step = 5
                    st.rerun()

            with st.expander("⏱ Custom Paces (optional)", expanded=False):
                st.markdown(
                    '<p style="font-size:0.85rem;color:#8B92A5;">'
                    'Override auto-calculated paces if you know your current training paces. '
                    'Leave at 0 to let PaceForge calculate from your VDOT.</p>',
                    unsafe_allow_html=True,
                )
                pace_cols = st.columns(3)
                with pace_cols[0]:
                    easy_min = st.number_input("Easy min/km", 0, 10, wd.get("custom_easy_min", 0), key="wiz_easy_min")
                    easy_sec = st.number_input("Easy sec", 0, 59, wd.get("custom_easy_sec", 0), key="wiz_easy_sec")
                with pace_cols[1]:
                    marathon_min = st.number_input("Marathon min/km", 0, 10, wd.get("custom_marathon_min", 0), key="wiz_marathon_min")
                    marathon_sec = st.number_input("Marathon sec", 0, 59, wd.get("custom_marathon_sec", 0), key="wiz_marathon_sec")
                with pace_cols[2]:
                    threshold_min = st.number_input("Threshold min/km", 0, 10, wd.get("custom_threshold_min", 0), key="wiz_threshold_min")
                    threshold_sec = st.number_input("Threshold sec", 0, 59, wd.get("custom_threshold_sec", 0), key="wiz_threshold_sec")
                wd["custom_easy_min"] = easy_min
                wd["custom_easy_sec"] = easy_sec
                wd["custom_marathon_min"] = marathon_min
                wd["custom_marathon_sec"] = marathon_sec
                wd["custom_threshold_min"] = threshold_min
                wd["custom_threshold_sec"] = threshold_sec

            nav1, _ = st.columns(2)
            with nav1:
                if st.button("← Back", use_container_width=True, key="wiz_back_4"):
                    st.session_state.wizard_step = 3
                    st.rerun()

        # ── Step 5: Review & Generate ────────────────────────────────
        elif step == 5:
            st.markdown(
                '<p style="font-size:1rem;color:#C9CDD5;margin-bottom:0.5rem;">'
                'Review your configuration. The AI coach will design a personalised plan '
                'based on your fitness profile, goal, and schedule.</p>',
                unsafe_allow_html=True,
            )
            goal_info = GOAL_INFO.get(wd.get("goal_type", ""), {})
            td = wd.get("target_date", date.today() + timedelta(weeks=14))
            sd = wd.get("start_date", date.today())
            weeks_avail = (td - sd).days // 7
            th = wd.get("target_h", 0)
            tm = wd.get("target_m", 0)
            target_str = f"{th}h {tm:02d}m" if (th + tm) > 0 else "Auto (from fitness data)"

            st.markdown(
                f'<div style="background:#1E2028;border-radius:10px;padding:16px;margin-bottom:1rem;">'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
                f'<div><span style="color:#8B92A5;font-size:0.8rem;">GOAL</span><br/>'
                f'<span style="font-weight:700;font-size:1.1rem;">{goal_info.get("icon","")} {wd.get("goal_type","").replace("_"," ")}</span></div>'
                f'<div><span style="color:#8B92A5;font-size:0.8rem;">RACE DATE</span><br/>'
                f'<span style="font-weight:700;">{td.strftime("%b %d, %Y")}</span></div>'
                f'<div><span style="color:#8B92A5;font-size:0.8rem;">TRAINING WEEKS</span><br/>'
                f'<span style="font-weight:700;">{weeks_avail} weeks ({sd.strftime("%b %d")} → {td.strftime("%b %d")})</span></div>'
                f'<div><span style="color:#8B92A5;font-size:0.8rem;">TARGET TIME</span><br/>'
                f'<span style="font-weight:700;">{target_str}</span></div>'
                f'<div><span style="color:#8B92A5;font-size:0.8rem;">EXPERIENCE</span><br/>'
                f'<span style="font-weight:700;">{wd.get("experience","intermediate").capitalize()}</span></div>'
                f'<div><span style="color:#8B92A5;font-size:0.8rem;">TRAINING DAYS</span><br/>'
                f'<span style="font-weight:700;">{len(wd.get("training_days",[]))} days/week</span></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            target_secs = (th * 3600 + tm * 60) if (th + tm) > 0 else None
            custom_easy = (wd.get("custom_easy_min", 0) * 60 + wd.get("custom_easy_sec", 0)) or None
            custom_marathon = (wd.get("custom_marathon_min", 0) * 60 + wd.get("custom_marathon_sec", 0)) or None
            custom_threshold = (wd.get("custom_threshold_min", 0) * 60 + wd.get("custom_threshold_sec", 0)) or None

            nav1, nav2 = st.columns(2)
            with nav1:
                if st.button("← Back", use_container_width=True, key="wiz_back_5"):
                    st.session_state.wizard_step = 4
                    st.rerun()
            with nav2:
                if st.button("🚀 Generate Plan", type="primary", use_container_width=True, key="wiz_generate"):
                    with st.spinner("🤖 AI Coach is designing your personalised plan..."):
                        r = requests.post(
                            f"{API_BASE}/plan/generate",
                            json={
                                "goal_type": wd.get("goal_type", "HALF_MARATHON"),
                                "target_date": str(td),
                                "target_time_seconds": target_secs,
                                "experience_level": wd.get("experience", "intermediate"),
                                "training_days": wd.get("training_days", []),
                                "long_run_day": wd.get("long_run_day", "sunday"),
                                "start_date": str(sd),
                                "custom_easy_pace": custom_easy,
                                "custom_marathon_pace": custom_marathon,
                                "custom_threshold_pace": custom_threshold,
                            },
                            headers=_auth_headers(),
                            timeout=60,
                        )
                        if r.status_code == 200:
                            st.session_state.plans.append(r.json())
                            st.session_state.wizard_step = 1
                            st.session_state.wizard_data = {}
                            st.success("Plan generated! Scroll down to review.")
                            st.rerun()
                        else:
                            st.error(f"Error: {_error_detail(r)}")

    plan = st.session_state.plans
    if plan:
        st.markdown("---")

      # ── Iterate over all plans ───────────────────────────────────────
    for p_idx, plan in enumerate(st.session_state.plans):
        plan_id = plan.get("plan_id", "")
        plan_name = plan.get("name", "Training Plan")
        created_at = plan.get("created_at", "")
        goal_type = plan.get("goal_type", "")
        target_dt = plan.get("target_date", "")
        total_wks = plan.get("total_weeks", 0)
        accepted = plan.get("accepted", False)
        status_color = "#00D26A" if accepted else "#FF9800"
        status_text = "✓ Added to Calendar" if accepted else "Draft — Review & Accept"

        goal_icon = GOAL_INFO.get(goal_type, {}).get("icon", "🏃")
        st.markdown(
            f'<div style="background:#1E2028;border-radius:10px;padding:16px;margin-bottom:0.75rem;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
            f'<div>'
            f'<div style="font-size:1.2rem;font-weight:700;">{goal_icon} {plan_name}</div>'
            f'<div style="color:#8B92A5;font-size:0.8rem;margin-top:2px;">'
            f'Created {created_at} · {goal_type.replace("_"," ")} · {total_wks} weeks · Race {target_dt}'
            f'</div></div>'
            f'<span style="background:{status_color}22;color:{status_color};padding:4px 12px;'
            f'border-radius:12px;font-size:0.8rem;font-weight:600;">{status_text}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── AI Coach Explanation ─────────────────────────────────────
        rationale = plan.get("rationale", "")
        tips = plan.get("tips", [])
        athlete_summary = plan.get("athlete_summary", "")
        pace_source = plan.get("pace_source", "")
        plan_vdot = plan.get("vdot")

        # Always show this section (athlete data + optional AI rationale)
        with st.expander("🧠 Plan Intelligence", expanded=(p_idx == len(st.session_state.plans) - 1)):
            # Athlete profile data used
            if athlete_summary or pace_source:
                summary_parts = []
                if plan_vdot:
                    summary_parts.append(f'<span style="color:#FFD600;font-weight:600;">VDOT {plan_vdot:.1f}</span>')
                if pace_source:
                    summary_parts.append(f'<span style="color:#8B92A5;">Paces from: {pace_source}</span>')
                st.markdown(
                    f'<div style="background:#1A2332;border-left:3px solid #FFD600;padding:12px 16px;'
                    f'border-radius:0 8px 8px 0;margin-bottom:1rem;">'
                    f'<div style="font-weight:600;color:#FFD600;margin-bottom:6px;">📊 Athlete Data Used</div>'
                    f'<div style="color:#C9CDD5;font-size:0.85rem;line-height:1.6;">'
                    f'{"<br>".join(summary_parts)}'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if athlete_summary:
                    # Split the summary into readable items
                    items = [s.strip() for s in athlete_summary.split(" · ") if s.strip()]
                    if items:
                        items_html = "".join(
                            f'<div style="padding:3px 0;color:#C9CDD5;font-size:0.85rem;">'
                            f'<span style="color:#60A5FA;margin-right:6px;">▸</span>{item}</div>'
                            for item in items
                            if not item.startswith("Pace source:")  # already shown above
                        )
                        st.markdown(
                            f'<div style="padding:0 16px 8px 16px;">{items_html}</div>',
                            unsafe_allow_html=True,
                        )

            if rationale:
                st.markdown(
                    f'<div style="background:#1A2332;border-left:3px solid #2563EB;padding:12px 16px;'
                    f'border-radius:0 8px 8px 0;margin-bottom:1rem;">'
                    f'<div style="font-weight:600;color:#60A5FA;margin-bottom:4px;">Plan Rationale</div>'
                    f'<div style="color:#C9CDD5;font-size:0.9rem;">{rationale}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if tips:
                st.markdown(
                    '<div style="font-weight:600;color:#00D26A;margin-bottom:8px;">💡 Personalised Tips</div>',
                    unsafe_allow_html=True,
                )
                for tip in tips:
                    st.markdown(
                        f'<div style="padding:6px 0 6px 16px;border-left:2px solid #2A2D35;'
                        f'color:#C9CDD5;font-size:0.9rem;margin-bottom:4px;">{tip}</div>',
                        unsafe_allow_html=True,
                    )

        # ── Accept / Remove / Adapt / Delete buttons ──
        btn_cols = st.columns([1, 1, 1, 1])
        with btn_cols[0]:
            if not accepted:
                if st.button("✓ Add to Calendar", type="primary", use_container_width=True, key=f"accept_{plan_id}"):
                    with st.spinner("Accepting plan..."):
                        r = requests.post(
                            f"{API_BASE}/plan/accept",
                            json={"plan_id": plan_id, "accepted": True},
                            headers=_auth_headers(),
                            timeout=10,
                        )
                        if r.status_code == 200:
                            pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                            if pr.status_code == 200:
                                st.session_state.plans = pr.json()
                            st.success("Plan added to your calendar!")
                            st.rerun()
                        else:
                            st.error(f"Error: {_error_detail(r)}")
            else:
                if st.button("Remove from Calendar", use_container_width=True, key=f"remove_{plan_id}"):
                    with st.spinner("Removing..."):
                        r = requests.post(
                            f"{API_BASE}/plan/accept",
                            json={"plan_id": plan_id, "accepted": False},
                            headers=_auth_headers(),
                            timeout=10,
                        )
                        if r.status_code == 200:
                            pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                            if pr.status_code == 200:
                                st.session_state.plans = pr.json()
                            st.info("Plan removed from calendar.")
                            st.rerun()
                        else:
                            st.error(f"Error: {_error_detail(r)}")
        with btn_cols[1]:
            if st.button("Adapt Plan", use_container_width=True, key=f"adapt_{plan_id}"):
                with st.spinner("Adapting plan based on latest fitness..."):
                    r = requests.post(
                        f"{API_BASE}/plan/adapt?plan_id={plan_id}",
                        headers=_auth_headers(),
                        timeout=30,
                    )
                    if r.status_code == 200:
                        pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                        if pr.status_code == 200:
                            st.session_state.plans = pr.json()
                        st.success("Plan adapted!")
                        st.rerun()
                    else:
                        st.error(f"Error: {_error_detail(r)}")
        with btn_cols[2]:
            if st.button("🗑 Delete Plan", use_container_width=True, key=f"delete_{plan_id}"):
                with st.spinner("Deleting plan..."):
                    r = requests.delete(
                        f"{API_BASE}/plan/{plan_id}",
                        headers=_auth_headers(),
                        timeout=10,
                    )
                    if r.status_code == 200:
                        pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                        if pr.status_code == 200:
                            st.session_state.plans = pr.json()
                        st.success("Plan deleted.")
                        st.rerun()
                    else:
                        st.error(f"Error: {_error_detail(r)}")

        # ── Training Paces ──
        paces = {}
        for key in ["easy_pace", "marathon_pace", "threshold_pace", "interval_pace"]:
            val = plan.get(key)
            if val:
                pm, ps = divmod(int(val), 60)
                paces[key.replace("_pace", "").title()] = f"{pm}:{ps:02d}"

        if paces:
            pace_cols = st.columns(len(paces))
            for i, (zone, val) in enumerate(paces.items()):
                color = _PACE_COLORS.get(zone, "#00D26A")
                with pace_cols[i]:
                    st.markdown(
                        f'<div class="pf-pace-card">'
                        f'<div class="pf-pace-zone" style="color:{color};">{zone}</div>'
                        f'<div class="pf-pace-value">{val}<span class="pf-metric-unit">/km</span></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # ── Weekly Breakdown ──
        plan_paces = {
            k: plan.get(k)
            for k in ("easy_pace", "marathon_pace", "threshold_pace", "interval_pace", "repetition_pace")
        }
        for week in plan.get("weeks", []):
            phase = week.get("phase", "base").lower()
            phase_bg = _PHASE_COLORS.get(phase, "rgba(0,210,106,0.12)")
            phase_color = _PHASE_TEXT.get(phase, "#00D26A")
            focus = week.get("focus", "")
            total_km = week.get("total_distance_km", 0)

            with st.expander(
                f"Week {week['week_number']} — {total_km} km"
                f"{' | ' + focus if focus else ''}",
                expanded=False,
            ):
                st.markdown(
                    f'<div class="pf-week-header">'
                    f'<span class="pf-week-phase" style="background:{phase_bg};color:{phase_color};">'
                    f'{phase}'
                    f'</span>'
                    f'<span class="pf-week-meta">{total_km} km total</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                for _w_idx, w in enumerate(week.get("workouts", [])):
                    wtype = w.get("workout_type", "rest")
                    color = _WORKOUT_COLORS.get(wtype, "#607D8B")

                    if wtype == "rest":
                        st.markdown(
                            f'<div class="pf-workout-item">'
                            f'<div class="pf-workout-dot" style="background:#9E9E9E;"></div>'
                            f'<div class="pf-workout-info">'
                            f'<div class="pf-workout-name" style="color:#8B92A5;">'
                            f'{w.get("scheduled_date", "")} — Rest Day'
                            f'</div></div></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        dist = round(w.get("estimated_distance_meters", 0) / 1000, 1)
                        purpose = w.get("purpose", "")
                        notes = w.get("notes", "")
                        detail_parts = [f"{dist} km"]
                        if purpose:
                            detail_parts.append(purpose)
                        detail = " · ".join(detail_parts)

                        st.markdown(
                            f'<div class="pf-workout-item">'
                            f'<div class="pf-workout-dot" style="background:{color};"></div>'
                            f'<div class="pf-workout-info">'
                            f'<div class="pf-workout-name">'
                            f'{w.get("scheduled_date", "")} — {w["name"]}'
                            f'</div>'
                            f'<div class="pf-workout-detail">{detail}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                        with st.expander(f"📋 {w['name']} — Workout Structure", expanded=False):
                            workout_dict = {
                                "name": w["name"],
                                "workout_type": wtype,
                                "purpose": purpose,
                                "notes": notes,
                                "steps": w.get("steps", []),
                                "estimated_distance_meters": w.get("estimated_distance_meters", 0),
                                "estimated_duration_seconds": w.get("estimated_duration_seconds", 0),
                            }
                            st.markdown(
                                _render_workout_detail(workout_dict, plan_paces),
                                unsafe_allow_html=True,
                            )

        if p_idx < len(st.session_state.plans) - 1:
            st.markdown('<hr style="border-color:#2A2D35;margin:1.5rem 0;" />', unsafe_allow_html=True)


# ── Tab 3: Calendar ──────────────────────────────────────────────────

with tab_calendar:
    st.markdown('<div class="pf-section-header">Training Calendar</div>', unsafe_allow_html=True)

    if True:
        # Sync button only visible when Garmin is connected
        if st.session_state.garmin_logged_in and st.button("\U0001f504 Sync Activities from Garmin", key="sync_activities_btn"):
            with st.spinner("Fetching activities from Garmin Connect..."):
                try:
                    r = requests.get(
                        f"{API_BASE}/activities?days=240&sync=true",
                        headers=_auth_headers(),
                        timeout=60,
                    )
                    if r.status_code == 200:
                        st.session_state["garmin_activities"] = r.json()
                        st.session_state["cal_selected_event"] = None
                        st.session_state["cal_selected_detail"] = None
                        st.success(f"Synced {len(r.json())} activities!")
                    else:
                        st.error(f"Failed to sync: {_error_detail(r)}")
                except requests.ConnectionError:
                    st.error("Cannot reach API.")

        cal_events = []

        # ── Past activities from Garmin ──
        # Collect activity IDs already matched to planned workouts (to avoid duplicates)
        _matched_act_ids = set()
        for _p in st.session_state.plans:
            if not _p.get("accepted", False):
                continue
            for _wk in _p.get("weeks", []):
                for _w in _wk.get("workouts", []):
                    if _w.get("matched_activity_id"):
                        _matched_act_ids.add(_w["matched_activity_id"])

        garmin_acts = st.session_state.get("garmin_activities", [])
        for i, act in enumerate(garmin_acts):
            # Skip activities already matched to a planned workout
            if act.get("activity_id") in _matched_act_ids:
                continue
            dist = round(act.get("distance_meters", 0) / 1000, 1)
            pace = act.get("avg_pace_sec_per_km")
            pace_str = ""
            if pace:
                pm, ps = divmod(int(pace), 60)
                pace_str = f" @ {pm}:{ps:02d}/km"

            # Parse date from start_time
            start_raw = act.get("start_time", "")
            start_date = start_raw[:10] if start_raw else ""

            cal_events.append({
                "id": f"act_{i}",
                "title": f"✓ {act.get('name', 'Activity')} ({dist}km{pace_str})",
                "start": start_date,
                "allDay": True,
                "backgroundColor": "#00D26A",
                "borderColor": "#00D26A",
                "editable": False,
                "extendedProps": {
                    "source": "garmin",
                    "activity_id": act.get("activity_id"),
                    "distance_km": dist,
                    "pace": pace_str,
                    "duration_seconds": act.get("duration_seconds", 0),
                    "avg_hr": act.get("avg_hr"),
                },
            })

        # ── Planned workouts from all accepted plans ──
        for plan in st.session_state.plans:
            if not plan.get("accepted", False):
                continue
            plan_id = plan.get("plan_id", "")
            for week in plan.get("weeks", []):
                for j, w in enumerate(week.get("workouts", [])):
                    wtype = w.get("workout_type", "rest")
                    if wtype == "rest":
                        continue
                    dist = round(w.get("estimated_distance_meters", 0) / 1000, 1)
                    is_completed = w.get("completed", False)
                    prefix = "✅" if is_completed else "📋"
                    bg_color = "#00D26A" if is_completed else _WORKOUT_COLORS.get(wtype, "#607D8B")
                    cal_events.append({
                        "id": f"plan_w{week['week_number']}_{j}",
                        "title": f"{prefix} {w['name']} ({dist}km)",
                        "start": w.get("scheduled_date", ""),
                        "allDay": True,
                        "backgroundColor": bg_color,
                        "borderColor": bg_color,
                        "editable": not is_completed,
                        "extendedProps": {
                            "source": "plan",
                            "workout_type": wtype,
                            "purpose": w.get("purpose", ""),
                            "name": w["name"],
                            "steps": json.dumps(w.get("steps", [])),
                            "notes": w.get("notes", ""),
                            "estimated_distance_meters": w.get("estimated_distance_meters", 0),
                            "estimated_duration_seconds": w.get("estimated_duration_seconds", 0),
                            "plan_id": plan_id,
                            "completed": is_completed,
                            "matched_activity_id": w.get("matched_activity_id"),
                            "completion_analysis": w.get("completion_analysis", ""),
                            "completion_metrics": json.dumps(w.get("completion_metrics") or {}),
                            "user_rpe": w.get("user_rpe"),
                            "user_notes": w.get("user_notes", ""),
                        },
                    })

        if not cal_events:
            st.markdown(
                '<p style="color:#8B92A5;text-align:center;margin:2rem 0;">'
                'Click <b>Sync Activities from Garmin</b> to load your workout history, '
                'or generate a training plan to see future workouts.</p>',
                unsafe_allow_html=True,
            )
        else:
            # Legend + push controls row
            legend_cols = st.columns([3, 1, 1])
            with legend_cols[0]:
                st.markdown(
                    '<div style="display:flex;flex-wrap:wrap;gap:1rem;margin-bottom:0.5rem;font-size:0.8rem;">'
                    '<span style="color:#00D26A;">● Completed</span>'
                    '<span style="color:#2196F3;">● Long Run</span>'
                    '<span style="color:#4CAF50;">● Easy</span>'
                    '<span style="color:#FF9800;">● Tempo</span>'
                    '<span style="color:#F44336;">● Speed</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if plan and plan.get("accepted", False):
                    st.caption("Drag planned workouts (📋) to reschedule · Click any event for details")
            with legend_cols[1]:
                if plan and plan.get("accepted", False):
                    if st.button("🤖 AI Review Plan", key="cal_ai_review_btn", use_container_width=True):
                        plan_id = plan.get("plan_id", "")
                        with st.spinner("AI is reviewing your progress..."):
                            try:
                                r = requests.post(
                                    f"{API_BASE}/plan/ai-review",
                                    params={"plan_id": plan_id} if plan_id else {},
                                    headers=_auth_headers(),
                                    timeout=120,
                                )
                                if r.status_code == 200:
                                    review_data = r.json()
                                    st.session_state["ai_review_result"] = review_data.get("review", "")
                                    # Refresh plans
                                    pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                                    if pr.status_code == 200:
                                        st.session_state.plans = pr.json()
                                    st.rerun()
                                else:
                                    st.error(f"Review failed: {_error_detail(r)}")
                            except requests.ConnectionError:
                                st.error("Cannot reach API.")
            with legend_cols[2]:
                if plan and plan.get("accepted", False) and st.session_state.garmin_logged_in:
                    if st.button("Push Plan to Garmin", type="primary", key="cal_push_btn", use_container_width=True):
                        with st.spinner("Pushing all workouts to Garmin..."):
                            try:
                                r = requests.post(
                                    f"{API_BASE}/plan/push",
                                    json={},
                                    headers=_auth_headers(),
                                    timeout=120,
                                )
                                if r.status_code == 200:
                                    data = r.json()
                                    st.success(f"✓ Pushed {data.get('workouts_pushed', '?')} workouts to Garmin!")
                                else:
                                    st.error(f"Push failed: {_error_detail(r)}")
                            except requests.ConnectionError:
                                st.error("Cannot reach API.")

            # ── Side-by-side: Calendar (left) + Detail panel (right) ──
            cal_col, detail_col = st.columns([2, 3])

            with cal_col:
                cal_options = {
                    "editable": True,
                    "selectable": False,
                    "headerToolbar": {
                        "left": "today prev,next",
                        "center": "title",
                        "right": "dayGridMonth,dayGridWeek",
                    },
                    "initialView": "dayGridMonth",
                    "initialDate": str(date.today()),
                    "contentHeight": 420,
                }

                cal_css = """
                    .fc { background: #1A1D23; color: #FAFAFA; border: none; }
                    .fc-theme-standard td, .fc-theme-standard th { border-color: #2D3139; }
                    .fc-theme-standard .fc-scrollgrid { border-color: #2D3139; }
                    .fc-col-header-cell { background: #242830; }
                    .fc-col-header-cell-cushion { color: #8B92A5; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
                    .fc-daygrid-day-number { color: #8B92A5; font-size: 0.8rem; }
                    .fc-day-today { background: rgba(0,210,106,0.06) !important; }
                    .fc-event { cursor: pointer; font-size: 0.72em; border-radius: 5px; padding: 1px 4px; border: none !important; }
                    .fc-event-title { font-weight: 600; }
                    .fc-button { background: #242830 !important; border: 1px solid #3A3F4B !important; color: #FAFAFA !important; font-size: 0.8rem !important; }
                    .fc-button:hover { background: #2D3139 !important; }
                    .fc-button-active { background: #00D26A !important; color: #1A1D23 !important; border-color: #00D26A !important; }
                    .fc-toolbar-title { font-size: 1rem !important; font-weight: 700; color: #FAFAFA; }
                """

                from streamlit_calendar import calendar as st_calendar

                result = st_calendar(
                    events=cal_events,
                    options=cal_options,
                    custom_css=cal_css,
                    key="plan_calendar",
                )

                # Handle drag-to-reschedule
                if result and result.get("callback") == "eventChange":
                    ev = result["eventChange"]
                    ev_props = ev["event"].get("extendedProps", {})
                    if ev_props.get("source") == "plan":
                        old_start = ev["oldEvent"]["start"]
                        new_start = ev["event"]["start"]
                        wk_name = ev_props.get("name", ev["event"]["title"])
                        r = requests.post(
                            f"{API_BASE}/plan/reschedule",
                            json={
                                "workout_name": wk_name,
                                "old_date": old_start[:10],
                                "new_date": new_start[:10],
                            },
                            headers=_auth_headers(),
                            timeout=10,
                        )
                        if r.status_code == 200:
                            st.success(f"Moved to {new_start[:10]} — click **Push Plan to Garmin** to sync")
                        else:
                            st.error("Failed to reschedule")

                # Handle event click — store in session_state for the detail panel
                if result and result.get("callback") == "eventClick":
                    ev_data = result["eventClick"]["event"]
                    props = ev_data.get("extendedProps", {})
                    st.session_state["cal_selected_event"] = {
                        "title": ev_data.get("title", ""),
                        "start": ev_data.get("start", ""),
                        "props": props,
                    }
                    # Pre-fetch Garmin activity detail if needed
                    act_id_to_fetch = None
                    if props.get("source") == "garmin" and props.get("activity_id"):
                        act_id_to_fetch = props["activity_id"]
                    elif props.get("source") == "plan" and props.get("completed") and props.get("matched_activity_id"):
                        act_id_to_fetch = props["matched_activity_id"]

                    if act_id_to_fetch:
                        try:
                            r = requests.get(
                                f"{API_BASE}/activities/{act_id_to_fetch}",
                                headers=_auth_headers(),
                                timeout=30,
                            )
                            if r.status_code == 200:
                                st.session_state["cal_selected_detail"] = r.json()
                            else:
                                st.session_state["cal_selected_detail"] = None
                        except requests.ConnectionError:
                            st.session_state["cal_selected_detail"] = None
                    else:
                        st.session_state["cal_selected_detail"] = None

            # ── Detail panel (right column) ──
            with detail_col:
                sel = st.session_state.get("cal_selected_event")
                if sel is None:
                    st.markdown(
                        '<div style="display:flex;align-items:center;justify-content:center;height:400px;color:#8B92A5;text-align:center;">'
                        '<div><div style="font-size:2rem;margin-bottom:0.5rem;">👆</div>'
                        '<div style="font-size:0.9rem;">Click an event on the calendar<br>to view details</div></div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    props = sel["props"]
                    ev_title = sel["title"]
                    ev_date = sel.get("start", "")[:10]

                    if props.get("source") == "garmin":
                        st.markdown(
                            f'<div style="font-weight:700;font-size:1rem;margin-bottom:0.25rem;">✓ {ev_title}</div>'
                            f'<div style="color:#8B92A5;font-size:0.8rem;margin-bottom:0.5rem;">{ev_date}</div>',
                            unsafe_allow_html=True,
                        )
                        detail_data = st.session_state.get("cal_selected_detail")
                        if detail_data:
                            _render_garmin_activity_detail(detail_data)
                        else:
                            # Fallback: show basic info from event props
                            dur = props.get("duration_seconds", 0)
                            dur_m, dur_s = divmod(int(dur), 60)
                            dist_km = props.get("distance_km", 0)
                            pace_str = props.get("pace", "")
                            hr_text = f" · Avg HR: {props['avg_hr']} bpm" if props.get("avg_hr") else ""
                            st.markdown(
                                f'<div class="pf-card">'
                                f'<div style="color:#FAFAFA;">📏 {dist_km}km · ⏱ {dur_m}:{dur_s:02d}{pace_str}{hr_text}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        # Planned workout detail
                        is_completed = props.get("completed", False)
                        steps_json = props.get("steps", "[]")
                        try:
                            steps_list = json.loads(steps_json) if isinstance(steps_json, str) else steps_json
                        except (json.JSONDecodeError, TypeError):
                            steps_list = []
                        workout_dict = {
                            "name": props.get("name", ev_title),
                            "workout_type": props.get("workout_type", ""),
                            "purpose": props.get("purpose", ""),
                            "notes": props.get("notes", ""),
                            "steps": steps_list,
                            "estimated_distance_meters": props.get("estimated_distance_meters", 0),
                            "estimated_duration_seconds": props.get("estimated_duration_seconds", 0),
                        }
                        plan_paces = None
                        accepted_plans = [p for p in st.session_state.plans if p.get("accepted")]
                        if accepted_plans:
                            plan_paces = {
                                k: accepted_plans[0].get(k)
                                for k in ("easy_pace", "marathon_pace", "threshold_pace", "interval_pace", "repetition_pace")
                            }

                        # Show completion status header
                        if is_completed:
                            st.markdown(
                                '<div style="background:#1B3A2A;border:1px solid #00D26A;border-radius:8px;padding:0.5rem 0.75rem;margin-bottom:0.5rem;">'
                                '<span style="color:#00D26A;font-weight:700;">✅ Completed</span></div>',
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            _render_workout_detail(workout_dict, plan_paces),
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="color:#8B92A5;font-size:0.75rem;margin-top:0.5rem;">📅 Scheduled: {ev_date}</div>',
                            unsafe_allow_html=True,
                        )

                        # Show completion metrics if available
                        if is_completed:
                            metrics_json = props.get("completion_metrics", "{}")
                            try:
                                metrics = json.loads(metrics_json) if isinstance(metrics_json, str) else (metrics_json or {})
                            except (json.JSONDecodeError, TypeError):
                                metrics = {}

                            # Merge in live-fetched detail EARLY so richer data populates cards
                            detail_data = metrics.get("detail") or {}
                            live_detail = st.session_state.get("cal_selected_detail")
                            if live_detail:
                                live_summary = live_detail.get("summary") or {}
                                live_dto = live_summary.get("summaryDTO") or live_summary
                                if not detail_data.get("splits") and live_detail.get("splits"):
                                    detail_data["splits"] = live_detail["splits"]
                                if not detail_data.get("hr_zones") and live_detail.get("hr_zones"):
                                    detail_data["hr_zones"] = live_detail["hr_zones"]
                                # Back-fill metrics from live Garmin detail
                                for src_key, tgt_key in [
                                    ("distance", "distance_meters"),
                                    ("duration", "duration_seconds"),
                                    ("averageHR", "avg_hr"),
                                    ("maxHR", "max_hr"),
                                    ("averageRunningCadenceInStepsPerMinute", "avg_running_cadence"),
                                    ("calories", "calories"),
                                    ("elevationGain", "elevation_gain"),
                                    ("trainingEffect", "training_effect_aerobic"),
                                    ("anaerobicTrainingEffect", "training_effect_anaerobic"),
                                ]:
                                    if not metrics.get(tgt_key) and live_dto.get(src_key):
                                        metrics[tgt_key] = live_dto[src_key]
                                # Avg pace from live speed
                                if not metrics.get("avg_pace_sec_per_km") and live_dto.get("averageSpeed"):
                                    metrics["avg_pace_sec_per_km"] = 1000 / live_dto["averageSpeed"]

                            # ── Rich metric cards grid ──
                            act_dist = metrics.get("distance_meters", 0)
                            act_dur = metrics.get("duration_seconds", 0)
                            act_pace = metrics.get("avg_pace_sec_per_km")
                            act_hr = metrics.get("avg_hr")
                            act_max_hr = metrics.get("max_hr")
                            act_cadence = metrics.get("avg_running_cadence")
                            act_calories = metrics.get("calories")
                            act_elevation = metrics.get("elevation_gain")
                            act_aero_te = metrics.get("training_effect_aerobic")
                            act_anaero_te = metrics.get("training_effect_anaerobic")

                            cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:0.35rem;margin:0.5rem 0;">'
                            card_data = []
                            if act_dist:
                                card_data.append(("Distance", f"{act_dist/1000:.1f}km", "📏"))
                            if act_dur:
                                dm, ds = divmod(int(act_dur), 60)
                                card_data.append(("Duration", f"{dm}:{ds:02d}", "⏱"))
                            if act_pace:
                                pm, ps = divmod(int(act_pace), 60)
                                card_data.append(("Avg Pace", f"{pm}:{ps:02d}/km", "🏃"))
                            if act_hr:
                                card_data.append(("Avg HR", f"{int(act_hr)} bpm", "❤️"))
                            if act_max_hr:
                                card_data.append(("Max HR", f"{int(act_max_hr)} bpm", "💓"))
                            if act_cadence:
                                card_data.append(("Cadence", f"{int(act_cadence * 2)} spm", "🦶"))
                            if act_calories:
                                card_data.append(("Calories", f"{int(act_calories)}", "🔥"))
                            if act_elevation:
                                card_data.append(("Elevation", f"{int(act_elevation)}m", "⛰️"))
                            if act_aero_te:
                                card_data.append(("Aerobic TE", f"{act_aero_te:.1f}", "🫁"))
                            if act_anaero_te:
                                card_data.append(("Anaerobic TE", f"{act_anaero_te:.1f}", "💪"))

                            for label, val, icon in card_data:
                                cards_html += (
                                    f'<div style="background:#242830;border-radius:8px;padding:0.35rem;text-align:center;">'
                                    f'<div style="font-size:0.6rem;color:#8B92A5;">{icon} {label}</div>'
                                    f'<div style="font-size:0.85rem;font-weight:700;color:#FAFAFA;">{val}</div>'
                                    f'</div>'
                                )
                            cards_html += '</div>'
                            if card_data:
                                st.markdown(cards_html, unsafe_allow_html=True)

                            # ── Planned vs Actual comparison ──
                            planned_dist = props.get("estimated_distance_meters", 0)
                            planned_dur = props.get("estimated_duration_seconds", 0)
                            if planned_dist and act_dist:
                                dist_diff = ((act_dist - planned_dist) / planned_dist) * 100
                                dist_color = "#00D26A" if abs(dist_diff) < 15 else "#FF9800"
                                comp_html = f'<span style="color:{dist_color};">Dist: {dist_diff:+.0f}%</span>'
                                if planned_dur and act_dur:
                                    dur_diff = ((act_dur - planned_dur) / planned_dur) * 100
                                    dur_color = "#00D26A" if abs(dur_diff) < 15 else "#FF9800"
                                    comp_html += f' · <span style="color:{dur_color};">Duration: {dur_diff:+.0f}%</span>'
                                st.markdown(
                                    f'<div style="font-size:0.75rem;color:#8B92A5;margin-bottom:0.5rem;">vs Planned: {comp_html}</div>',
                                    unsafe_allow_html=True,
                                )

                            # ── Splits table (from detail data merged above) ──
                            splits_data = detail_data.get("splits") or {}
                            hr_zones_data = detail_data.get("hr_zones") or {}
                            laps = splits_data.get("lapDTOs") or []
                            if laps:
                                rows_html = ""
                                for idx, lap in enumerate(laps, 1):
                                    lap_dist = lap.get("distance", 0)
                                    lap_speed = lap.get("averageSpeed", 0)
                                    lap_pace = (1000 / lap_speed) if lap_speed else 0
                                    lap_hr = lap.get("averageHR", 0)
                                    pace_str = _fmt_pace(lap_pace) if lap_pace else "--"
                                    dist_str = f"{lap_dist / 1000:.2f}" if lap_dist else "--"
                                    hr_str = f"{int(lap_hr)}" if lap_hr else "--"
                                    rows_html += (
                                        f'<tr style="border-bottom:1px solid #2D3139;">'
                                        f'<td style="padding:4px 8px;text-align:center;color:#FAFAFA;">{idx}</td>'
                                        f'<td style="padding:4px 8px;text-align:center;color:#FAFAFA;">{dist_str}</td>'
                                        f'<td style="padding:4px 8px;text-align:center;color:#FAFAFA;">{pace_str}</td>'
                                        f'<td style="padding:4px 8px;text-align:center;color:#FAFAFA;">{hr_str}</td>'
                                        f'</tr>'
                                    )
                                table_html = (
                                    '<div style="margin:0.5rem 0;">'
                                    '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;">'
                                    '<thead><tr style="border-bottom:2px solid #3A3F4B;">'
                                    '<th style="padding:4px 8px;color:#8B92A5;font-weight:600;">Split</th>'
                                    '<th style="padding:4px 8px;color:#8B92A5;font-weight:600;">Dist (km)</th>'
                                    '<th style="padding:4px 8px;color:#8B92A5;font-weight:600;">Pace</th>'
                                    '<th style="padding:4px 8px;color:#8B92A5;font-weight:600;">HR</th>'
                                    '</tr></thead><tbody>'
                                    f'{rows_html}'
                                    '</tbody></table></div>'
                                )
                                st.markdown(table_html, unsafe_allow_html=True)

                            # ── HR Zones chart ──
                            hr_list = hr_zones_data if isinstance(hr_zones_data, list) else hr_zones_data.get("hrTimeInZones", []) if isinstance(hr_zones_data, dict) else []
                            if hr_list:
                                import plotly.graph_objects as go
                                zone_labels = []
                                zone_seconds = []
                                zone_colors_list = ["#3F51B5", "#2196F3", "#4CAF50", "#FF9800", "#F44336"]
                                for zd in hr_list:
                                    zn = zd.get("zoneNumber") or zd.get("zone", 0)
                                    secs = zd.get("secsInZone", 0)
                                    zone_labels.append(f"Z{zn}")
                                    zone_seconds.append(secs)
                                if any(s > 0 for s in zone_seconds):
                                    zone_minutes = [s / 60 for s in zone_seconds]
                                    fig_hr = go.Figure(go.Bar(
                                        y=zone_labels, x=zone_minutes, orientation="h",
                                        marker_color=zone_colors_list[:len(zone_labels)],
                                        text=[_fmt_duration(s) for s in zone_seconds],
                                        textposition="auto", textfont=dict(color="#FAFAFA", size=8),
                                    ))
                                    fig_hr.update_layout(
                                        plot_bgcolor="#1A1D23", paper_bgcolor="#1A1D23", font_color="#FAFAFA",
                                        margin=dict(l=25, r=15, t=8, b=20), height=130,
                                        xaxis=dict(title="Time (min)", gridcolor="#2D3139", title_font=dict(size=9)),
                                        yaxis=dict(gridcolor="#2D3139"), bargap=0.3,
                                    )
                                    st.plotly_chart(fig_hr, use_container_width=True, key=f"hr_zones_{ev_date}_{props.get('name','')}")

                            # ── AI Analysis ──
                            analysis = props.get("completion_analysis", "")
                            if analysis:
                                st.markdown(
                                    f'<div class="pf-card" style="margin-top:0.5rem;border-left:3px solid #00D26A;">'
                                    f'<div style="color:#8B92A5;font-size:0.7rem;margin-bottom:0.25rem;">🤖 AI ANALYSIS</div>'
                                    f'<div style="color:#FAFAFA;font-size:0.82rem;">{analysis}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                wo_name = props.get("name", "")
                                p_id = props.get("plan_id", "")
                                if st.button("🤖 Analyze with AI", key=f"analyze_{ev_date}_{wo_name}", use_container_width=True):
                                    with st.spinner("AI is analyzing your workout..."):
                                        try:
                                            r = requests.post(
                                                f"{API_BASE}/plan/analyze-workout",
                                                json={"plan_id": p_id, "workout_name": wo_name, "scheduled_date": ev_date},
                                                headers=_auth_headers(),
                                                timeout=60,
                                            )
                                            if r.status_code == 200:
                                                result = r.json()
                                                st.markdown(
                                                    f'<div class="pf-card" style="border-left:3px solid #00D26A;">'
                                                    f'<div style="color:#8B92A5;font-size:0.7rem;margin-bottom:0.25rem;">🤖 AI ANALYSIS</div>'
                                                    f'<div style="color:#FAFAFA;font-size:0.82rem;">{result.get("analysis", "")}</div>'
                                                    f'</div>',
                                                    unsafe_allow_html=True,
                                                )
                                                pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                                                if pr.status_code == 200:
                                                    st.session_state.plans = pr.json()
                                            else:
                                                st.error(f"Analysis failed: {_error_detail(r)}")
                                        except requests.ConnectionError:
                                            st.error("Cannot reach API.")

                            # ── User Feedback Section ──
                            st.markdown("---")
                            wo_name = props.get("name", "")
                            p_id = props.get("plan_id", "")
                            existing_rpe = props.get("user_rpe")
                            existing_notes = props.get("user_notes", "")

                            st.markdown('<div style="color:#8B92A5;font-size:0.75rem;margin-bottom:0.25rem;">📝 How did it feel?</div>', unsafe_allow_html=True)
                            rpe_val = st.slider(
                                "Rate of Perceived Exertion",
                                min_value=1, max_value=10,
                                value=existing_rpe if existing_rpe else 5,
                                key=f"rpe_{ev_date}_{wo_name}",
                                help="1 = Very Light, 5 = Moderate, 10 = Maximum",
                            )
                            rpe_labels = {1: "Very Light", 2: "Light", 3: "Light-Moderate", 4: "Moderate",
                                          5: "Moderate-Hard", 6: "Hard", 7: "Very Hard", 8: "Very Hard+",
                                          9: "Near Maximum", 10: "Maximum"}
                            st.caption(f"RPE {rpe_val}: {rpe_labels.get(rpe_val, '')}")

                            user_notes_val = st.text_area(
                                "Notes (optional)",
                                value=existing_notes or "",
                                placeholder="How did it feel? Any pain, fatigue, or highlights?",
                                key=f"notes_{ev_date}_{wo_name}",
                                height=70,
                            )

                            if st.button("💾 Save & Re-analyze", key=f"feedback_{ev_date}_{wo_name}", use_container_width=True):
                                with st.spinner("Saving feedback and re-analyzing..."):
                                    try:
                                        r = requests.post(
                                            f"{API_BASE}/plan/workout-feedback",
                                            json={
                                                "plan_id": p_id,
                                                "workout_name": wo_name,
                                                "scheduled_date": ev_date,
                                                "rpe": rpe_val,
                                                "notes": user_notes_val,
                                            },
                                            headers=_auth_headers(),
                                            timeout=60,
                                        )
                                        if r.status_code == 200:
                                            result = r.json()
                                            st.success("Feedback saved!")
                                            st.markdown(
                                                f'<div class="pf-card" style="border-left:3px solid #00D26A;">'
                                                f'<div style="color:#8B92A5;font-size:0.7rem;margin-bottom:0.25rem;">🤖 UPDATED AI ANALYSIS</div>'
                                                f'<div style="color:#FAFAFA;font-size:0.82rem;">{result.get("analysis", "")}</div>'
                                                f'</div>',
                                                unsafe_allow_html=True,
                                            )
                                            pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                                            if pr.status_code == 200:
                                                st.session_state.plans = pr.json()
                                        else:
                                            st.error(f"Failed: {_error_detail(r)}")
                                    except requests.ConnectionError:
                                        st.error("Cannot reach API.")
                        else:
                            # Not completed — offer to match a Garmin activity
                            wo_name = props.get("name", "")
                            p_id = props.get("plan_id", "")
                            garmin_acts = st.session_state.get("garmin_activities", [])

                            # Filter activities on or near the scheduled date
                            matching_acts = []
                            for act in garmin_acts:
                                act_date = (act.get("start_time", "") or "")[:10]
                                if act_date == ev_date:
                                    matching_acts.append(act)

                            if matching_acts:
                                st.markdown("---")
                                st.markdown('<div style="color:#8B92A5;font-size:0.75rem;margin-bottom:0.25rem;">🔗 Match Garmin Activity</div>', unsafe_allow_html=True)
                                act_options = {
                                    f"{a.get('name', 'Activity')} ({round(a.get('distance_meters', 0)/1000, 1)}km)": a.get("activity_id")
                                    for a in matching_acts
                                }
                                selected_act = st.selectbox(
                                    "Select activity",
                                    list(act_options.keys()),
                                    key=f"match_sel_{ev_date}_{wo_name}",
                                    label_visibility="collapsed",
                                )
                                if st.button("✅ Match & Complete", key=f"match_{ev_date}_{wo_name}", use_container_width=True):
                                    act_id = act_options[selected_act]
                                    with st.spinner("Matching..."):
                                        try:
                                            r = requests.post(
                                                f"{API_BASE}/plan/match-workout",
                                                json={"plan_id": p_id, "workout_name": wo_name, "scheduled_date": ev_date, "activity_id": act_id},
                                                headers=_auth_headers(),
                                                timeout=30,
                                            )
                                            if r.status_code == 200:
                                                st.success("Workout matched!")
                                                pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                                                if pr.status_code == 200:
                                                    st.session_state.plans = pr.json()
                                                st.session_state.cal_selected_event = None
                                                st.rerun()
                                            else:
                                                st.error(f"Match failed: {_error_detail(r)}")
                                        except requests.ConnectionError:
                                            st.error("Cannot reach API.")

                        if not is_completed:
                            if st.button("🗑 Delete Workout", key=f"del_{ev_date}_{props.get('name','')}", use_container_width=True):
                                r = requests.post(
                                    f"{API_BASE}/plan/delete-workout",
                                    json={"workout_name": props.get("name", ""), "scheduled_date": ev_date},
                                    headers=_auth_headers(),
                                    timeout=10,
                                )
                                if r.status_code == 200:
                                    pr = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                                    if pr.status_code == 200:
                                        st.session_state.plans = pr.json()
                                    st.session_state.cal_selected_event = None
                                    st.success("Workout deleted!")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {_error_detail(r)}")

            # ── AI Review Results (below calendar) ──
            ai_review = st.session_state.get("ai_review_result")
            if not ai_review and plan and plan.get("adaptation_notes"):
                ai_review = plan.get("adaptation_notes")
            if ai_review:
                st.markdown("---")
                st.markdown(
                    '<div style="font-weight:700;font-size:1rem;color:#00D26A;margin-bottom:0.5rem;">🤖 AI Plan Review</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(ai_review)

# ── Tab 4: HYROX Race Results ────────────────────────────────────────

def _hyrox_fmt_time(secs):
    """Format seconds as H:MM:SS or M:SS."""
    if secs is None:
        return "—"
    total = int(secs)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


with tab_hyrox:
    import plotly.graph_objects as go

    # ── Load cached HYROX data on tab open ──
    if "hyrox_data" not in st.session_state:
        st.session_state.hyrox_data = None
    if "hyrox_loading" not in st.session_state:
        st.session_state.hyrox_loading = False

    # Auto-load from DB on first visit
    if st.session_state.hyrox_data is None and not st.session_state.hyrox_loading:
        try:
            r = requests.get(f"{API_BASE}/hyrox/results", headers=_auth_headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("results"):
                    st.session_state.hyrox_data = data
        except Exception:
            pass

    hx_data = st.session_state.hyrox_data
    has_results = hx_data and hx_data.get("results")

    # ── Header + Search / Refresh ──
    if has_results:
        hdr_col1, hdr_col2, hdr_col3 = st.columns([3, 1, 1])
        with hdr_col1:
            st.markdown(
                f'<div style="font-size:1.2rem;font-weight:700;color:#FF9800;margin-bottom:0.5rem;">'
                f'🔥 HYROX Results — {hx_data.get("search_name", "")}'
                f'<span style="color:#8B92A5;font-size:0.85rem;margin-left:12px;">'
                f'{len(hx_data["results"])} race(s)</span></div>',
                unsafe_allow_html=True,
            )
        with hdr_col3:
            if st.button("🗑️ New Search", key="hyrox_clear_top_btn"):
                requests.delete(f"{API_BASE}/hyrox/results", headers=_auth_headers(), timeout=10)
                st.session_state.hyrox_data = None
                st.session_state.hyrox_preview = None
                st.session_state.hyrox_search_params = {}
                st.rerun()
        with hdr_col2:
            if st.button("🔄 Refresh Results", key="hyrox_refresh_btn"):
                with st.spinner("Re-scraping HYROX results..."):
                    r = requests.post(f"{API_BASE}/hyrox/refresh", headers=_auth_headers(), timeout=120)
                    if r.status_code == 200:
                        st.session_state.hyrox_data = r.json()
                        st.success(f"Updated! Found {len(st.session_state.hyrox_data['results'])} races.")
                        st.rerun()
                    else:
                        st.error(f"Refresh failed: {_error_detail(r)}")
    else:
        st.markdown(
            '<div style="font-size:1.2rem;font-weight:700;color:#FF9800;margin-bottom:0.5rem;">'
            '🔥 HYROX Race Results</div>'
            '<p style="color:#8B92A5;margin-bottom:1rem;">Search for your HYROX race results by name. '
            'Results are saved to your profile permanently.</p>',
            unsafe_allow_html=True,
        )

    # ── Search form ──
    if "hyrox_preview" not in st.session_state:
        st.session_state.hyrox_preview = None  # list of summaries from search preview
    if "hyrox_search_params" not in st.session_state:
        st.session_state.hyrox_search_params = {}

    if not has_results:
        preview = st.session_state.hyrox_preview

        # Step 1: Search form
        if preview is None:
            with st.form("hyrox_search_form"):
                sc1, sc2, sc3, sc4 = st.columns([2, 2, 1, 1])
                with sc1:
                    search_surname = st.text_input("Last Name / Surname", placeholder="e.g. Perez Rodriguez")
                with sc2:
                    search_firstname = st.text_input("First Name (optional)", placeholder="e.g. Victor")
                with sc3:
                    search_gender = st.selectbox("Gender", ["M", "F"], index=0)
                with sc4:
                    search_div = st.selectbox("Division", ["All", "HYROX", "HYROX PRO", "Doubles", "Relay", "PRO Doubles"])
                submitted = st.form_submit_button("🔍 Search HYROX Results", use_container_width=True)
                if submitted and search_surname:
                    div_map = {"All": "all", "HYROX": "hyrox", "HYROX PRO": "hyrox_pro",
                               "Doubles": "hyrox_doubles", "Relay": "hyrox_relay", "PRO Doubles": "hyrox_pro_doubles"}
                    div_code = div_map.get(search_div, "all")
                    with st.spinner(f"Searching HYROX for '{search_surname}'..."):
                        r = requests.get(
                            f"{API_BASE}/hyrox/search",
                            params={"name": search_surname, "firstname": search_firstname,
                                    "division": div_code, "gender": search_gender},
                            headers=_auth_headers(),
                            timeout=120,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            summaries = data.get("summaries", [])
                            if summaries:
                                st.session_state.hyrox_preview = summaries
                                st.session_state.hyrox_search_params = {
                                    "name": search_surname, "firstname": search_firstname,
                                    "gender": search_gender,
                                }
                                st.rerun()
                            else:
                                st.warning("No results found. Try a different name or division.")
                        else:
                            st.error(f"Search failed: {_error_detail(r)}")

        # Step 2: Preview list — let user select which races are theirs
        else:
            params = st.session_state.hyrox_search_params
            display_name = params.get("firstname", "")
            if display_name:
                display_name += " " + params.get("name", "")
            else:
                display_name = params.get("name", "")

            st.markdown(
                f'<div style="font-size:1rem;font-weight:600;color:#E0E0E0;margin-bottom:0.5rem;">'
                f'Found {len(preview)} race(s) matching <span style="color:#FF9800;">{display_name}</span>. '
                f'Select the races that belong to you:</div>',
                unsafe_allow_html=True,
            )

            with st.form("hyrox_select_form"):
                selections = []
                for i, s in enumerate(preview):
                    athlete_name = s.get("name", "Unknown")
                    city = s.get("city", "")
                    total = s.get("total_time", "")
                    rank = s.get("rank", "")
                    label = f"{athlete_name} — {city}"
                    if total:
                        label += f" — {total}"
                    if rank:
                        label += f" (#{rank})"
                    checked = st.checkbox(label, value=True, key=f"hyrox_sel_{i}")
                    selections.append((checked, s.get("athlete_url", "")))

                col_confirm, col_back = st.columns(2)
                with col_confirm:
                    confirmed = st.form_submit_button("✅ Import Selected Races", use_container_width=True)
                with col_back:
                    go_back = st.form_submit_button("← Back to Search", use_container_width=True)

                if confirmed:
                    selected_urls = [url for checked, url in selections if checked and url]
                    if not selected_urls:
                        st.warning("Please select at least one race.")
                    else:
                        with st.spinner(f"Fetching full split data for {len(selected_urls)} race(s)... (this may take a moment)"):
                            r = requests.post(
                                f"{API_BASE}/hyrox/confirm",
                                json={**params, "selected_urls": selected_urls},
                                headers=_auth_headers(),
                                timeout=180,
                            )
                            if r.status_code == 200:
                                st.session_state.hyrox_data = r.json()
                                st.session_state.hyrox_preview = None
                                st.session_state.hyrox_search_params = {}
                                st.success(f"Imported {len(st.session_state.hyrox_data['results'])} race(s)!")
                                st.rerun()
                            else:
                                st.error(f"Import failed: {_error_detail(r)}")

                if go_back:
                    st.session_state.hyrox_preview = None
                    st.session_state.hyrox_search_params = {}
                    st.rerun()

    # ── Display results ──
    if has_results:
        results = hx_data["results"]

        # ── Race selector ──
        race_options = []
        for i, race in enumerate(results):
            city = race.get("event_date") or race.get("city", "Unknown")
            div = race.get("division", "")
            total = race.get("total_time_display", "")
            rank = race.get("rank", "")
            label = f"{city}"
            if div:
                label += f" ({div})"
            if total:
                label += f" — {total}"
            if rank:
                label += f" #{rank}"
            race_options.append(label)

        selected_idx = st.selectbox(
            "Select a race to analyze",
            range(len(race_options)),
            format_func=lambda i: race_options[i],
            key="hyrox_race_selector",
        )

        selected_race = results[selected_idx]

        # ── Fetch analysis for selected race ──
        analysis_data = None
        try:
            r = requests.get(
                f"{API_BASE}/hyrox/analyze/{selected_idx}",
                headers=_auth_headers(), timeout=15,
            )
            if r.status_code == 200:
                analysis_data = r.json()
        except Exception:
            pass

        if analysis_data:
            ana = analysis_data["analysis"]
            prios = analysis_data["priorities"]

            # ══════════════════════════════════════════
            # RACE SUMMARY CARDS
            # ══════════════════════════════════════════
            rc1, rc2, rc3, rc4, rc5 = st.columns(5)
            with rc1:
                st.markdown(_metric_card("Total Time", ana["total_time_display"], "", "orange"), unsafe_allow_html=True)
            with rc2:
                st.markdown(_metric_card("Running", ana["total_running_display"], f'{ana["running_pct"]}%', "blue"), unsafe_allow_html=True)
            with rc3:
                st.markdown(_metric_card("Stations", ana["total_stations_display"], f'{ana["station_pct"]}%', "cyan"), unsafe_allow_html=True)
            with rc4:
                st.markdown(_metric_card("Roxzone", ana["roxzone_display"], f'{ana["roxzone_pct"]}%', "red"), unsafe_allow_html=True)
            with rc5:
                st.markdown(_metric_card("Avg Run Pace", ana["avg_run_pace_display"], "", "green"), unsafe_allow_html=True)

            # ══════════════════════════════════════════
            # RACE WATERFALL — all segments
            # ══════════════════════════════════════════
            st.markdown("")
            split_ana = ana.get("split_analysis", [])
            if split_ana:
                wf_labels = [s["display"] for s in split_ana]
                wf_times = [s["athlete_seconds"] / 60 if s["athlete_seconds"] else 0 for s in split_ana]
                wf_colors = []
                for s in split_ana:
                    is_run = s["name"].startswith("Running")
                    if is_run:
                        wf_colors.append("#2196F3")
                    else:
                        wf_colors.append("#FF9800")

                fig_wf = go.Figure()
                fig_wf.add_trace(go.Bar(
                    x=wf_labels,
                    y=wf_times,
                    marker_color=wf_colors,
                    text=[s["athlete_display"] for s in split_ana],
                    textposition="outside",
                    textfont=dict(color="#C9CDD5", size=9),
                    hovertemplate="%{x}: %{text}<extra></extra>",
                ))
                fig_wf.update_layout(
                    title="Race Segment Breakdown",
                    yaxis_title="Time (minutes)",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C9CDD4", size=11),
                    margin=dict(l=40, r=20, t=40, b=80), height=350,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickangle=-45),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                )
                st.plotly_chart(fig_wf, use_container_width=True, key="hyrox_waterfall")

            # ══════════════════════════════════════════
            # RUNNING ANALYSIS — 8-bar splits + fade
            # ══════════════════════════════════════════
            st.markdown("")
            run_splits = ana.get("run_splits", [])
            if run_splits and any(s["seconds"] for s in run_splits):
                fade = ana["fade_pct"]
                running_class = ana["running_class"]
                class_colors = {"Strong Compromised Runner": "#00D26A", "Moderate Drop-off": "#FF9800", "Severe Fade": "#F44336"}
                cls_c = class_colors.get(running_class, "#8B92A5")

                st.markdown(
                    f'<div style="display:flex;gap:12px;align-items:center;margin-bottom:8px;">'
                    f'<span style="background:{cls_c}22;color:{cls_c};padding:4px 14px;border-radius:12px;'
                    f'font-size:0.85rem;font-weight:600;">{running_class}</span>'
                    f'<span style="color:#8B92A5;font-size:0.85rem;">Pace fade: {fade:.1f}%</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                run_labels = [s["name"] for s in run_splits]
                run_secs = [s["seconds"] or 0 for s in run_splits]
                # Green-to-red gradient
                run_colors = []
                for i in range(len(run_secs)):
                    ratio = i / max(len(run_secs) - 1, 1)
                    r_val = int(0 + ratio * 244)
                    g_val = int(210 - ratio * 143)
                    b_val = int(106 - ratio * 52)
                    run_colors.append(f"rgb({r_val},{g_val},{b_val})")

                fig_runs = go.Figure()
                fig_runs.add_trace(go.Bar(
                    x=run_labels,
                    y=[s / 60 for s in run_secs],
                    marker_color=run_colors,
                    text=[_hyrox_fmt_time(s) for s in run_secs],
                    textposition="outside",
                    textfont=dict(color="#C9CDD5", size=11),
                    hovertemplate="%{x}: %{text}/km<extra></extra>",
                ))
                fig_runs.update_layout(
                    title="Running Splits (8 x 1km)",
                    yaxis_title="Pace (min/km)", yaxis_autorange="reversed",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#C9CDD4", size=11),
                    margin=dict(l=50, r=20, t=40, b=40), height=300,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                )
                st.plotly_chart(fig_runs, use_container_width=True, key="hyrox_run_splits")

            # ══════════════════════════════════════════
            # STATION BENCHMARKS — vs field + top 3
            # ══════════════════════════════════════════
            st.markdown("")
            station_splits = [s for s in split_ana if not s["name"].startswith("Running") and s["name"] != "Roxzone_Time"]
            if station_splits:
                st.markdown(
                    '<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin-bottom:6px;">'
                    'Station Performance vs Benchmarks</div>',
                    unsafe_allow_html=True,
                )
                bench_html = (
                    '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #2D3139;">'
                    '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.78rem;">Station</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Your Time</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Field Avg</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Top 3 Avg</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">vs Field</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">vs Top 3</th>'
                    '</tr>'
                )
                for s in station_splits:
                    gap_f = s["gap_vs_field"]
                    gap_t = s["gap_vs_top3"]
                    f_color = "#00D26A" if gap_f < 0 else "#F44336"
                    t_color = "#00D26A" if gap_t is not None and gap_t < 0 else "#F44336" if gap_t is not None else "#8B92A5"
                    f_text = f'{gap_f:+.0f}s'
                    t_text = f'{gap_t:+.0f}s' if gap_t is not None else "—"
                    bench_html += (
                        f'<tr style="border-bottom:1px solid #2D313922;">'
                        f'<td style="padding:8px;color:#FAFAFA;font-weight:500;">{s["display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FFD600;font-weight:600;">{s["athlete_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#C9CDD5;">{s["field_avg_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#C9CDD5;">{s["top3_avg_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:{f_color};font-weight:600;">{f_text}</td>'
                        f'<td style="padding:8px;text-align:center;color:{t_color};font-weight:600;">{t_text}</td>'
                        f'</tr>'
                    )
                bench_html += '</table></div>'
                st.markdown(bench_html, unsafe_allow_html=True)

            # ══════════════════════════════════════════
            # TRAINING PRIORITIES — ranked
            # ══════════════════════════════════════════
            if prios:
                st.markdown("")
                st.markdown(
                    '<div style="font-weight:600;color:#F44336;font-size:0.85rem;margin-bottom:6px;">'
                    '🎯 Training Priorities (Biggest Improvement Potential)</div>',
                    unsafe_allow_html=True,
                )
                # Show top 8 priorities
                top_prios = prios[:8]
                prio_html = (
                    '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #2D3139;">'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">#</th>'
                    '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.78rem;">Segment</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Your Time</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Top 3 Avg</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Gap</th>'
                    '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Score</th>'
                    '</tr>'
                )
                priority_colors = ["#F44336", "#F44336", "#F44336", "#FF9800", "#FF9800", "#FFD600", "#FFD600", "#8B92A5"]
                for i, p in enumerate(top_prios):
                    pc = priority_colors[i] if i < len(priority_colors) else "#8B92A5"
                    t_icon = "🏃" if p["is_running"] else "💪"
                    prio_html += (
                        f'<tr style="border-bottom:1px solid #2D313922;">'
                        f'<td style="padding:8px;text-align:center;color:{pc};font-weight:700;">#{p["rank"]}</td>'
                        f'<td style="padding:8px;color:#FAFAFA;font-weight:500;">{t_icon} {p["display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FFD600;">{p["athlete_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#C9CDD5;">{p["top3_avg_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#F44336;font-weight:600;">+{p["gap_seconds"]:.0f}s</td>'
                        f'<td style="padding:8px;text-align:center;color:{pc};font-weight:600;">{p["priority_score"]:.1f}</td>'
                        f'</tr>'
                    )
                prio_html += '</table></div>'
                st.markdown(prio_html, unsafe_allow_html=True)

            # ══════════════════════════════════════════
            # AI IMPROVEMENT PLAN — based on weaknesses
            # ══════════════════════════════════════════
            if prios:
                st.markdown("")
                st.markdown(
                    '<div style="font-weight:600;color:#AB47BC;font-size:0.85rem;margin-bottom:6px;">'
                    '🤖 AI Improvement Plan</div>'
                    '<p style="color:#8B92A5;font-size:0.8rem;margin-bottom:8px;">'
                    'Ask the AI coach to create a targeted training plan to improve your weakest areas.</p>',
                    unsafe_allow_html=True,
                )
                if st.button("Generate HYROX Improvement Plan", key="hyrox_ai_plan_btn", type="primary"):
                    # Build context from priorities
                    weakness_lines = []
                    for p_item in prios[:6]:
                        icon = "Running" if p_item["is_running"] else "Station"
                        weakness_lines.append(
                            f"- {icon}: {p_item['display']} — Your time: {p_item['athlete_display']}, "
                            f"Top 3 avg: {p_item['top3_avg_display']}, Gap: +{p_item['gap_seconds']:.0f}s"
                        )
                    race_city = selected_race.get("event_date") or selected_race.get("city", "")
                    race_total = selected_race.get("total_time_display", "")
                    coach_prompt = (
                        f"I just raced HYROX at {race_city} with a total time of {race_total}. "
                        f"Based on my race analysis, here are my biggest weaknesses ranked by improvement potential:\n\n"
                        + "\n".join(weakness_lines)
                        + "\n\nPlease create a specific 4-week training plan with weekly sessions "
                        "targeting these weaknesses. Include:\n"
                        "1. Specific exercises/drills for each weak station\n"
                        "2. Running sessions to improve my pace fade\n"
                        "3. How many sessions per week and what to focus on each day\n"
                        "4. Progression — how to increase difficulty over the 4 weeks\n"
                        "Keep it practical and time-efficient (assume I can train 5-6 days/week)."
                    )
                    with st.spinner("AI Coach is creating your improvement plan..."):
                        r_coach = requests.post(
                            f"{API_BASE}/coach/chat",
                            json={"message": coach_prompt},
                            headers=_auth_headers(),
                            timeout=60,
                        )
                        if r_coach.status_code == 200:
                            plan_reply = r_coach.json().get("reply", "")
                            st.markdown(
                                f'<div style="background:#1E2028;border:1px solid #AB47BC44;border-radius:10px;'
                                f'padding:16px;margin-top:8px;color:#E0E0E0;font-size:0.9rem;line-height:1.6;">'
                                f'{plan_reply}</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.error("AI Coach is unavailable. Make sure PACEFORGE_ANTHROPIC_API_KEY is configured.")

        # ══════════════════════════════════════════
        # RACE HISTORY — multi-race trends
        # ══════════════════════════════════════════
        if len(results) >= 2:
            st.markdown("")
            st.markdown(
                '<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin-bottom:6px;">'
                '📈 Race History</div>',
                unsafe_allow_html=True,
            )
            try:
                rp = requests.get(f"{API_BASE}/hyrox/progression", headers=_auth_headers(), timeout=15)
                if rp.status_code == 200:
                    prog = rp.json()
                    races_data = prog.get("races", [])

                    if races_data:
                        # Race summary table
                        hist_html = (
                            '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;margin-bottom:1rem;">'
                            '<table style="width:100%;border-collapse:collapse;">'
                            '<tr style="border-bottom:1px solid #2D3139;">'
                            '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">#</th>'
                            '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.78rem;">Event</th>'
                            '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Division</th>'
                            '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Total Time</th>'
                            '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Rank</th>'
                            '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Fade %</th>'
                            '</tr>'
                        )
                        for rd in races_data:
                            fade_c = "#00D26A" if rd["fade_pct"] < 8 else "#FF9800" if rd["fade_pct"] < 15 else "#F44336"
                            event_label = rd.get("event_date") or rd["city"]
                            hist_html += (
                                f'<tr style="border-bottom:1px solid #2D313922;">'
                                f'<td style="padding:8px;text-align:center;color:#8B92A5;">{rd["index"]}</td>'
                                f'<td style="padding:8px;color:#FAFAFA;font-weight:500;">{event_label}</td>'
                                f'<td style="padding:8px;text-align:center;color:#C9CDD5;">{rd["division"]}</td>'
                                f'<td style="padding:8px;text-align:center;color:#FFD600;font-weight:600;">{rd["total_display"]}</td>'
                                f'<td style="padding:8px;text-align:center;color:#C9CDD5;">{rd["rank"]}</td>'
                                f'<td style="padding:8px;text-align:center;color:{fade_c};">{rd["fade_pct"]:.1f}%</td>'
                                f'</tr>'
                            )
                        hist_html += '</table></div>'
                        st.markdown(hist_html, unsafe_allow_html=True)

                        # Total time trend chart
                        total_trend = prog.get("total_trend", [])
                        if len(total_trend) >= 2:
                            trend_labels = [rd.get("event_date") or rd["city"] for rd in races_data if rd["total_seconds"]]
                            fig_trend = go.Figure()
                            fig_trend.add_trace(go.Scatter(
                                x=trend_labels,
                                y=[t / 60 for t in total_trend],
                                mode="lines+markers",
                                line=dict(color="#FF9800", width=3),
                                marker=dict(size=10, color="#FF9800"),
                                hovertemplate="%{x}<br>%{y:.1f} min<extra></extra>",
                            ))
                            improving = prog.get("improving", False)
                            trend_title = "Total Time Trend"
                            if improving:
                                trend_title += " 📈 Improving!"
                            fig_trend.update_layout(
                                title=trend_title,
                                yaxis_title="Total Time (min)", yaxis_autorange="reversed",
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(color="#C9CDD4", size=11),
                                margin=dict(l=50, r=20, t=40, b=50), height=300,
                                xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickangle=-30),
                                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                            )
                            st.plotly_chart(fig_trend, use_container_width=True, key="hyrox_trend")

                        # Best race highlight
                        best = prog.get("best_race")
                        if best:
                            best_event = best.get("event_date") or best.get("city", "")
                            st.markdown(
                                f'<div style="background:#0D2818;border:1px solid #00D26A;border-radius:8px;'
                                f'padding:10px 16px;margin-top:8px;">'
                                f'<span style="color:#00D26A;font-weight:600;">🏆 Personal Best:</span> '
                                f'<span style="color:#FAFAFA;">{best["total_display"]}</span> '
                                f'<span style="color:#8B92A5;">at {best_event}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                        # ══════════════════════════════════════════
                        # STATION COMPARISON ACROSS RACES
                        # ══════════════════════════════════════════
                        station_cmp = prog.get("station_comparison", [])
                        if station_cmp and len(races_data) >= 2:
                            st.markdown("")
                            st.markdown(
                                '<div style="font-weight:600;color:#8B92A5;font-size:0.85rem;margin-bottom:6px;">'
                                '🔄 Station Comparison Across Races</div>',
                                unsafe_allow_html=True,
                            )

                            # Build comparison table
                            event_labels = [rd.get("event_date") or rd["city"] for rd in races_data]
                            cmp_html = (
                                '<div style="background:#1E2028;border-radius:10px;padding:12px 16px;overflow-x:auto;">'
                                '<table style="width:100%;border-collapse:collapse;">'
                                '<tr style="border-bottom:1px solid #2D3139;">'
                                '<th style="text-align:left;padding:8px;color:#8B92A5;font-size:0.78rem;">Segment</th>'
                            )
                            for ev in event_labels:
                                cmp_html += f'<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">{ev}</th>'
                            cmp_html += '<th style="text-align:center;padding:8px;color:#8B92A5;font-size:0.78rem;">Change</th>'
                            cmp_html += '</tr>'

                            for sc in station_cmp:
                                icon = "🏃" if sc["is_running"] else "💪"
                                cmp_html += '<tr style="border-bottom:1px solid #2D313922;">'
                                cmp_html += f'<td style="padding:8px;color:#FAFAFA;font-weight:500;">{icon} {sc["display"]}</td>'

                                # Per-race times — highlight best in green
                                race_times = sc["times"]
                                valid_secs = [t["seconds"] for t in race_times if t["seconds"]]
                                best_sec = min(valid_secs) if valid_secs else None

                                for t in race_times:
                                    if t["seconds"] is None:
                                        cmp_html += '<td style="padding:8px;text-align:center;color:#8B92A5;">—</td>'
                                    elif t["seconds"] == best_sec:
                                        cmp_html += f'<td style="padding:8px;text-align:center;color:#00D26A;font-weight:600;">{t["display"]}</td>'
                                    else:
                                        cmp_html += f'<td style="padding:8px;text-align:center;color:#C9CDD5;">{t["display"]}</td>'

                                # Improvement column
                                imp = sc.get("improvement_seconds")
                                if imp is not None and abs(imp) >= 1:
                                    if imp > 0:
                                        imp_c = "#00D26A"
                                        imp_text = f"-{int(imp)}s"
                                    else:
                                        imp_c = "#F44336"
                                        imp_text = f"+{int(abs(imp))}s"
                                    cmp_html += f'<td style="padding:8px;text-align:center;color:{imp_c};font-weight:600;">{imp_text}</td>'
                                else:
                                    cmp_html += '<td style="padding:8px;text-align:center;color:#8B92A5;">—</td>'
                                cmp_html += '</tr>'

                            cmp_html += '</table></div>'
                            st.markdown(cmp_html, unsafe_allow_html=True)

                            # Station comparison bar chart — stations only (not runs)
                            station_only = [sc for sc in station_cmp if not sc["is_running"] and sc["name"] != "Roxzone_Time"]
                            if station_only:
                                st.markdown("")
                                fig_cmp = go.Figure()
                                bar_colors = ["#FF9800", "#2196F3", "#00D26A", "#AB47BC", "#F44336", "#FFD600"]
                                for ri, rd in enumerate(races_data):
                                    race_label = rd.get("event_date") or rd["city"]
                                    y_vals = []
                                    for sc in station_only:
                                        t = sc["times"][ri]["seconds"] if ri < len(sc["times"]) else None
                                        y_vals.append(t / 60 if t else 0)
                                    fig_cmp.add_trace(go.Bar(
                                        name=race_label,
                                        x=[sc["display"] for sc in station_only],
                                        y=y_vals,
                                        marker_color=bar_colors[ri % len(bar_colors)],
                                        text=[sc["times"][ri]["display"] if ri < len(sc["times"]) else "—" for sc in station_only],
                                        textposition="outside",
                                        textfont=dict(color="#C9CDD5", size=9),
                                    ))
                                fig_cmp.update_layout(
                                    title="Station Times: Race-by-Race Comparison",
                                    yaxis_title="Time (min)",
                                    barmode="group",
                                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                    font=dict(color="#C9CDD4", size=11),
                                    margin=dict(l=50, r=20, t=40, b=80), height=380,
                                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickangle=-30),
                                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                                    legend=dict(font=dict(color="#8B92A5")),
                                )
                                st.plotly_chart(fig_cmp, use_container_width=True, key="hyrox_station_cmp")
            except Exception:
                pass

        # ── HYROX Performance Predictions (from fitness profile) ──
        # Show predictions based on running fitness data if profile analytics available
        analytics = st.session_state.get("analytics")
        if not analytics:
            try:
                r = requests.get(f"{API_BASE}/profile/analytics", headers=_auth_headers(), timeout=15)
                if r.status_code == 200:
                    analytics = r.json()
            except Exception:
                pass

        hx_pred = (analytics or {}).get("hyrox", {})
        sus_pace = hx_pred.get("sustainable_1km_pace")
        pred_splits = hx_pred.get("race_1km_splits", [])
        if sus_pace and pred_splits:
            st.markdown("")
            st.markdown(
                '<div style="font-size:1.05rem;font-weight:700;color:#FF9800;margin-bottom:0.5rem;">'
                '🏃 Running Performance Predictions</div>'
                '<div style="font-size:0.8rem;color:#8B92A5;margin-bottom:0.8rem;">'
                'Estimated from your Garmin fitness data (VO2max, threshold, training volume)</div>',
                unsafe_allow_html=True,
            )
            hxp1, hxp2, hxp3 = st.columns(3)
            with hxp1:
                pm, ps = divmod(int(sus_pace), 60)
                st.markdown(_metric_card("Predicted Race 1km Pace", f"{pm}:{ps:02d}", "/km", "orange"), unsafe_allow_html=True)
            with hxp2:
                total_run = hx_pred.get("total_running_time")
                run_str = _fmt_time(total_run) if total_run else "—"
                st.markdown(_metric_card("Predicted Running Time", run_str, "8×1km total", "blue"), unsafe_allow_html=True)
            with hxp3:
                comp_class = hx_pred.get("compromised_running_class", "—")
                fade_pct = hx_pred.get("pace_fade_pct", 0)
                st.markdown(_metric_card("Fade Classification", comp_class, f"{fade_pct:.1f}% fade", "green"), unsafe_allow_html=True)

        # ── "Clear Results" button ──
        st.markdown("")
        if st.button("🗑️ Clear saved results and search again", key="hyrox_clear_btn"):
            requests.delete(f"{API_BASE}/hyrox/results", headers=_auth_headers(), timeout=10)
            st.session_state.hyrox_data = None
            st.session_state.hyrox_preview = None
            st.session_state.hyrox_search_params = {}
            st.rerun()


# ── Tab 5: AI Coach ──────────────────────────────────────────────────

with tab_coach:
    st.markdown('<div class="pf-section-header">AI Running Coach</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8B92A5;margin-bottom:1rem;">Ask questions about your training and get personalized advice.</p>',
        unsafe_allow_html=True,
    )

    user_msg = st.text_area(
        "Your question",
        placeholder="How should I adjust if I missed two runs this week?",
        label_visibility="collapsed",
    )
    if st.button("Ask Coach", type="primary"):
        with st.spinner("Thinking..."):
            r = requests.post(
                f"{API_BASE}/coach/chat",
                json={"message": user_msg},
                headers=_auth_headers(),
                timeout=30,
            )
            if r.status_code == 200:
                st.markdown(
                    f'<div class="pf-chat-bubble">{r.json()["reply"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.error("Coach unavailable")


# ── Tab 6: User Profile ──────────────────────────────────────────────

with tab_user_settings:

    col_profile, col_garmin = st.columns(2, gap="large")

    # ── Account Information ──
    with col_profile:
        st.markdown('<div class="pf-section-header">Account Information</div>', unsafe_allow_html=True)

        with st.form("up_profile_form"):
            new_name = st.text_input("Name", value=st.session_state.user_name or "", key="up_name")
            new_email = st.text_input("Email", value=st.session_state.user_email or "", key="up_email")
            st.markdown(
                '<div style="margin-top:0.5rem;font-size:0.8rem;color:#8B92A5;">'
                "Leave blank to keep current password</div>",
                unsafe_allow_html=True,
            )
            new_password = st.text_input(
                "New Password", type="password", placeholder="min 8 characters", key="up_new_pw"
            )
            confirm_password = st.text_input(
                "Confirm New Password", type="password", key="up_confirm_pw"
            )
            st.markdown("---")
            current_password = st.text_input(
                "Current Password (required)", type="password", key="up_cur_pw"
            )
            save_clicked = st.form_submit_button("Save Changes", type="primary", use_container_width=True)

        if save_clicked:
            if not current_password:
                st.error("Current password is required to make changes.")
            elif new_password and new_password != confirm_password:
                st.error("New passwords do not match.")
            elif new_password and len(new_password) < 8:
                st.error("New password must be at least 8 characters.")
            else:
                payload = {"current_password": current_password}
                if new_name and new_name != st.session_state.user_name:
                    payload["name"] = new_name
                if new_email and new_email != st.session_state.user_email:
                    payload["email"] = new_email
                if new_password:
                    payload["new_password"] = new_password

                if len(payload) == 1:
                    st.info("No changes detected.")
                else:
                    try:
                        r = requests.patch(
                            f"{API_BASE}/auth/profile",
                            json=payload,
                            headers=_auth_headers(),
                            timeout=15,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            st.session_state.user_name = data["name"]
                            st.session_state.user_email = data["email"]
                            st.success("Profile updated!")
                            st.rerun()
                        else:
                            st.error(_error_detail(r))
                    except requests.ConnectionError:
                        st.error("Cannot reach API.")

    # ── Garmin Connect ──
    with col_garmin:
        st.markdown('<div class="pf-section-header">Garmin Connect</div>', unsafe_allow_html=True)

        if not st.session_state.garmin_logged_in:
            if not st.session_state.mfa_required:
                garmin_email = st.text_input("Garmin Email", key="up_garmin_email")
                garmin_password = st.text_input("Garmin Password", type="password", key="up_garmin_pw")
                if st.button(
                    "Connect to Garmin",
                    type="primary",
                    use_container_width=True,
                    key="up_garmin_connect",
                ):
                    try:
                        with st.spinner("Authenticating (may take up to 90s)..."):
                            r = requests.post(
                                f"{API_BASE}/garmin/login",
                                json={"email": garmin_email, "password": garmin_password},
                                headers=_auth_headers(),
                                timeout=120,
                            )
                        data = r.json()
                        if r.status_code == 200 and data.get("status") == "mfa_required":
                            st.session_state.mfa_required = True
                            st.info("Check your email for the verification code.")
                            st.rerun()
                        elif r.status_code == 200:
                            st.session_state.garmin_logged_in = True
                            st.success("Connected!")
                            st.rerun()
                        else:
                            st.error(f"Failed: {data.get('detail', r.text)}")
                    except requests.ReadTimeout:
                        st.error("Timed out. Wait a few minutes and retry.")
                    except requests.ConnectionError:
                        st.error("Cannot reach API.")
            else:
                st.info("Verification code sent to your email.")
                mfa_code = st.text_input("MFA Code", placeholder="123456", key="up_mfa_input")
                if st.button("Verify", type="primary", use_container_width=True, key="up_mfa_btn"):
                    try:
                        r = requests.post(
                            f"{API_BASE}/garmin/mfa",
                            json={"code": mfa_code},
                            headers=_auth_headers(),
                            timeout=30,
                        )
                        if r.status_code == 200:
                            st.session_state.mfa_required = False
                            st.session_state.garmin_logged_in = True
                            st.success("Verified — connected!")
                            st.rerun()
                        else:
                            st.error(f"MFA failed: {_error_detail(r)}")
                    except requests.ConnectionError:
                        st.error("Cannot reach API.")
        else:
            st.markdown(
                '<div style="background:#00D26A22;border:1px solid #00D26A44;'
                "border-radius:12px;padding:1.5rem;text-align:center;margin-bottom:1rem;\">"
                '<div style="font-size:2rem;margin-bottom:0.5rem;">⌚</div>'
                '<div style="color:#00D26A;font-weight:600;font-size:1.1rem;">Connected</div>'
                "</div>",
                unsafe_allow_html=True,
            )

            prof = st.session_state.get("profile")
            if prof:
                st.markdown(
                    f"**Display Name:** {prof.get('displayName', 'N/A')}  \n"
                    f"**Weight:** {prof.get('weight', 'N/A')} kg  \n"
                    f"**VO2Max Running:** {prof.get('vo2MaxRunning', 'N/A')}",
                )

            if st.button(
                "Refresh Profile",
                use_container_width=True,
                key="up_refresh_profile",
            ):
                r = requests.get(
                    f"{API_BASE}/profile", headers=_auth_headers(), timeout=30
                )
                if r.status_code == 200:
                    st.session_state.profile = r.json()
                    st.rerun()

    # ── Friends section ──
    st.markdown("---")
    st.markdown('<div class="pf-section-header">Friends</div>', unsafe_allow_html=True)

    # Load friends data
    try:
        friends_r = requests.get(f"{API_BASE}/friends", headers=_auth_headers(), timeout=15)
        friends_data = friends_r.json() if friends_r.status_code == 200 else {}
    except requests.ConnectionError:
        friends_data = {}
        st.error("Cannot reach API")

    friends_list = friends_data.get("friends", [])
    pending_reqs = friends_data.get("pending", [])
    sent_reqs = friends_data.get("sent", [])

    # Search and add friends
    search_q = st.text_input("🔍 Find people", placeholder="Search by name or email...", key="friend_search")
    if search_q and len(search_q) >= 2:
        try:
            sr = requests.get(
                f"{API_BASE}/users/search?q={search_q}",
                headers=_auth_headers(), timeout=10,
            )
            search_results = sr.json() if sr.status_code == 200 else []
        except requests.ConnectionError:
            search_results = []

        existing_friend_ids = {f["id"] for f in friends_list}
        pending_sent_ids = {r["id"] for r in sent_reqs}
        pending_recv_ids = {r["id"] for r in pending_reqs}

        for su in search_results:
            col_info, col_action = st.columns([3, 1])
            with col_info:
                st.markdown(
                    f'<div style="padding:0.4rem 0;">'
                    f'<span style="color:#FAFAFA;font-weight:500;">{su["name"]}</span>'
                    f'<span style="color:#8B92A5;font-size:0.85rem;margin-left:0.5rem;">{su["email"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_action:
                if su["id"] in existing_friend_ids:
                    st.markdown('<span style="color:#00D26A;font-size:0.85rem;">✅ Friends</span>',
                                unsafe_allow_html=True)
                elif su["id"] in pending_sent_ids:
                    st.markdown('<span style="color:#FFB800;font-size:0.85rem;">⏳ Pending</span>',
                                unsafe_allow_html=True)
                elif su["id"] in pending_recv_ids:
                    st.markdown('<span style="color:#4DA6FF;font-size:0.85rem;">📩 Accept below</span>',
                                unsafe_allow_html=True)
                else:
                    if st.button("Add", key=f"add_friend_{su['id']}", use_container_width=True):
                        try:
                            requests.post(
                                f"{API_BASE}/friends/request",
                                json={"recipient_id": su["id"]},
                                headers=_auth_headers(), timeout=10,
                            )
                            st.success(f"Request sent to {su['name']}")
                            st.rerun()
                        except requests.ConnectionError:
                            st.error("Cannot reach API")

    # Pending requests (incoming)
    if pending_reqs:
        st.markdown(f"**Pending Requests ({len(pending_reqs)})**")
        for pr in pending_reqs:
            col_info, col_accept, col_reject = st.columns([3, 1, 1])
            with col_info:
                st.markdown(
                    f'<div style="padding:0.3rem 0;color:#FAFAFA;">{pr["name"]}'
                    f'<span style="color:#8B92A5;font-size:0.8rem;margin-left:0.4rem;">{pr["email"]}</span></div>',
                    unsafe_allow_html=True,
                )
            with col_accept:
                if st.button("✅", key=f"accept_{pr['friendship_id']}", use_container_width=True):
                    try:
                        requests.post(
                            f"{API_BASE}/friends/respond",
                            json={"friendship_id": pr["friendship_id"], "accept": True},
                            headers=_auth_headers(), timeout=10,
                        )
                        st.rerun()
                    except requests.ConnectionError:
                        st.error("Cannot reach API")
            with col_reject:
                if st.button("❌", key=f"reject_{pr['friendship_id']}", use_container_width=True):
                    try:
                        requests.post(
                            f"{API_BASE}/friends/respond",
                            json={"friendship_id": pr["friendship_id"], "accept": False},
                            headers=_auth_headers(), timeout=10,
                        )
                        st.rerun()
                    except requests.ConnectionError:
                        st.error("Cannot reach API")

    # Friends list
    if friends_list:
        st.markdown(f"**Friends ({len(friends_list)})**")
        for fr in friends_list:
            col_info, col_remove = st.columns([4, 1])
            with col_info:
                fr_initials = "".join(w[0].upper() for w in fr["name"].split()[:2]) if fr.get("name") else "?"
                since = fr.get("friends_since", "")[:10]
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.6rem;padding:0.4rem 0;">'
                    f'<div style="width:32px;height:32px;border-radius:50%;background:#00D26A33;'
                    f'display:flex;align-items:center;justify-content:center;color:#00D26A;'
                    f'font-weight:700;font-size:0.8rem;">{fr_initials}</div>'
                    f'<div><span style="color:#FAFAFA;font-weight:500;">{fr["name"]}</span>'
                    f'<span style="color:#8B92A5;font-size:0.75rem;margin-left:0.3rem;">since {since}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with col_remove:
                if st.button("Remove", key=f"remove_friend_{fr['friendship_id']}",
                              use_container_width=True, type="secondary"):
                    try:
                        requests.delete(
                            f"{API_BASE}/friends/{fr['friendship_id']}",
                            headers=_auth_headers(), timeout=10,
                        )
                        st.rerun()
                    except requests.ConnectionError:
                        st.error("Cannot reach API")
    elif not pending_reqs:
        st.markdown(
            '<div style="text-align:center;padding:1.5rem;color:#8B92A5;">'
            "No friends yet — search for people above to connect!</div>",
            unsafe_allow_html=True,
        )


# ── Tab 7: Admin Panel ──────────────────────────────────────────────

if tab_admin is not None:
    with tab_admin:
        st.markdown('<div class="pf-section-header">User Management</div>', unsafe_allow_html=True)

        filter_col, refresh_col = st.columns([3, 1])
        with filter_col:
            status_filter = st.selectbox(
                "Filter by status",
                ["pending", "approved", "rejected", "all"],
                index=0,
                label_visibility="collapsed",
            )
        with refresh_col:
            if st.button("Refresh", use_container_width=True, key="admin_refresh"):
                st.rerun()

        query = f"?status={status_filter}" if status_filter != "all" else ""
        try:
            r = requests.get(
                f"{API_BASE}/admin/users{query}",
                headers=_auth_headers(),
                timeout=15,
            )
            if r.status_code == 200:
                users = r.json()
            else:
                users = []
                st.error(f"Failed to load users: {_error_detail(r)}")
        except requests.ConnectionError:
            users = []
            st.error("Cannot reach API")

        if not users:
            st.markdown(
                '<p style="color:#8B92A5;text-align:center;margin:2rem 0;">No users found.</p>',
                unsafe_allow_html=True,
            )
        else:
            # ── Summary metrics ──
            pending_count = sum(1 for u in users if u["status"] == "pending")
            approved_count = sum(1 for u in users if u["status"] == "approved")
            rejected_count = sum(1 for u in users if u["status"] == "rejected")

            if status_filter == "all":
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    st.markdown(_metric_card("Pending", str(pending_count), "", "orange"), unsafe_allow_html=True)
                with mc2:
                    st.markdown(_metric_card("Approved", str(approved_count), "", "green"), unsafe_allow_html=True)
                with mc3:
                    st.markdown(_metric_card("Rejected", str(rejected_count), "", "red"), unsafe_allow_html=True)
                st.markdown("")

            # ── User cards ──
            for u in users:
                badge_cls = u["status"]
                badge_label = u["status"].upper()
                if u.get("role") == "admin":
                    badge_cls = "admin"
                    badge_label = "ADMIN"

                with st.container(border=True):
                    info_col, action_col = st.columns([3, 1])
                    with info_col:
                        st.markdown(
                            f"""<div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.4rem;">
                                <span style="font-weight:700;font-size:1rem;">{u['name']}</span>
                                <span class="pf-badge {badge_cls}">{badge_label}</span>
                            </div>
                            <div style="color:#8B92A5;font-size:0.82rem;">
                                {u['email']}
                                {f" · Garmin: {u['garmin_email']}" if u.get('garmin_email') else ""}
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        if u.get("reason"):
                            st.caption(f"Reason: {u['reason']}")
                        st.caption(f"Registered: {u['created_at'][:10]}")
                    with action_col:
                        if u["status"] == "pending":
                            if st.button("Approve", key=f"approve_{u['id']}", type="primary", use_container_width=True):
                                r = requests.patch(
                                    f"{API_BASE}/admin/users/{u['id']}",
                                    json={"status": "approved"},
                                    headers=_auth_headers(),
                                    timeout=10,
                                )
                                if r.status_code == 200:
                                    st.success(f"Approved {u['name']}")
                                    st.rerun()
                                else:
                                    st.error("Failed")
                            if st.button("Reject", key=f"reject_{u['id']}", use_container_width=True):
                                r = requests.patch(
                                    f"{API_BASE}/admin/users/{u['id']}",
                                    json={"status": "rejected"},
                                    headers=_auth_headers(),
                                    timeout=10,
                                )
                                if r.status_code == 200:
                                    st.warning(f"Rejected {u['name']}")
                                    st.rerun()
                                else:
                                    st.error("Failed")
                        elif u["status"] == "approved" and u["role"] != "admin":
                            if st.button("Revoke", key=f"revoke_{u['id']}", use_container_width=True):
                                r = requests.patch(
                                    f"{API_BASE}/admin/users/{u['id']}",
                                    json={"status": "rejected"},
                                    headers=_auth_headers(),
                                    timeout=10,
                                )
                                if r.status_code == 200:
                                    st.warning(f"Revoked {u['name']}")
                                    st.rerun()
                                else:
                                    st.error("Failed")
