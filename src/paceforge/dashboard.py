"""PaceForge — Streamlit Dashboard (Dark Modern UI)."""

from __future__ import annotations

import base64
import json
from datetime import date, timedelta
from pathlib import Path

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="PaceForge", page_icon="🏃", layout="wide")

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
    "garmin_logged_in": False,
    "mfa_required": False,
    "profile": None,
    "plan": None,
    "page": "login",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def _auth_headers() -> dict:
    if st.session_state.jwt:
        return {"Authorization": f"Bearer {st.session_state.jwt}"}
    return {}


def _logout():
    for key in ["jwt", "role", "user_name", "garmin_logged_in", "mfa_required", "profile", "plan"]:
        st.session_state[key] = None if key not in ("garmin_logged_in", "mfa_required") else False
    st.session_state.page = "login"


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
    wtype = workout.get("workout_type", "")
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

    summary = detail.get("summary") or {}
    splits_data = detail.get("splits") or {}
    hr_zones_data = detail.get("hr_zones") or {}

    # ── Summary metric cards ──
    total_dist = summary.get("distance", 0)
    total_dur = summary.get("duration", 0)
    avg_speed = summary.get("averageSpeed", 0)
    avg_pace = (1000 / avg_speed) if avg_speed else 0
    avg_hr = summary.get("averageHR")
    max_hr = summary.get("maxHR")
    calories = summary.get("calories")
    elevation = summary.get("elevationGain")

    cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:0.5rem;margin-bottom:1rem;">'
    metric_data = [
        ("Distance", _fmt_dist(total_dist), "📏"),
        ("Duration", _fmt_duration(total_dur / 1000 if total_dur > 10000 else total_dur), "⏱"),
        ("Avg Pace", _fmt_pace(avg_pace) if avg_pace else "—", "🏃"),
    ]
    if avg_hr:
        metric_data.append(("Avg HR", f"{int(avg_hr)} bpm", "❤️"))
    if max_hr:
        metric_data.append(("Max HR", f"{int(max_hr)} bpm", "💓"))
    if calories:
        metric_data.append(("Calories", f"{int(calories)}", "🔥"))
    if elevation:
        metric_data.append(("Elevation", f"{int(elevation)}m", "⛰️"))

    for label, val, icon in metric_data:
        cards_html += (
            f'<div style="background:#242830;border-radius:10px;padding:0.6rem;text-align:center;">'
            f'<div style="font-size:0.7rem;color:#8B92A5;">{icon} {label}</div>'
            f'<div style="font-size:1rem;font-weight:700;color:#FAFAFA;">{val}</div>'
            f'</div>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── Splits ──
    laps = splits_data.get("lapDTOs") or []
    if laps:
        st.markdown('<div style="font-weight:600;font-size:0.9rem;margin-bottom:0.5rem;color:#00D26A;">Splits</div>', unsafe_allow_html=True)

        split_nums = []
        paces = []
        hrs = []
        rows_html = '<table style="width:100%;border-collapse:collapse;font-size:0.8rem;"><tr style="color:#8B92A5;border-bottom:1px solid #2D3139;"><th style="text-align:left;padding:4px;">Split</th><th>Distance</th><th>Pace</th><th>Avg HR</th></tr>'

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
                f'<td style="padding:4px;font-weight:600;">{i}</td>'
                f'<td style="text-align:center;">{_fmt_dist(lap_dist)}</td>'
                f'<td style="text-align:center;">{_fmt_pace(lap_pace)}</td>'
                f'<td style="text-align:center;">{int(lap_hr) if lap_hr else "—"} bpm</td>'
                f'</tr>'
            )
        rows_html += '</table>'
        st.markdown(f'<div class="pf-card" style="margin-bottom:1rem;">{rows_html}</div>', unsafe_allow_html=True)

        # Splits bar chart
        if paces:
            avg_p = sum(paces) / len(paces) if paces else 0
            colors = ["#00D26A" if p <= avg_p else "#FF5252" for p in paces]
            pace_labels = [_fmt_pace(p) for p in paces]

            fig = go.Figure(go.Bar(
                x=split_nums, y=paces,
                marker_color=colors,
                text=pace_labels,
                textposition="outside",
                textfont=dict(color="#FAFAFA", size=10),
            ))
            fig.update_layout(
                plot_bgcolor="#1A1D23",
                paper_bgcolor="#1A1D23",
                font_color="#FAFAFA",
                margin=dict(l=40, r=20, t=30, b=40),
                height=280,
                xaxis_title="Split",
                yaxis=dict(autorange="reversed", title="Pace (sec/km)", gridcolor="#2D3139"),
                xaxis=dict(gridcolor="#2D3139", dtick=1),
                bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True, key="splits_chart")

    # ── HR Zones ──
    hr_list = hr_zones_data if isinstance(hr_zones_data, list) else hr_zones_data.get("hrTimeInZones", [])
    if hr_list:
        st.markdown('<div style="font-weight:600;font-size:0.9rem;margin-bottom:0.5rem;color:#00D26A;">Heart Rate Zones</div>', unsafe_allow_html=True)
        zone_labels = []
        zone_seconds = []
        zone_colors_list = ["#3F51B5", "#2196F3", "#4CAF50", "#FF9800", "#F44336"]
        for zd in hr_list:
            zn = zd.get("zoneNumber") or zd.get("zone", 0)
            secs = zd.get("secsInZone", 0)
            zone_labels.append(f"Zone {zn}")
            zone_seconds.append(secs)

        fig_hr = go.Figure(go.Bar(
            y=zone_labels, x=zone_seconds,
            orientation="h",
            marker_color=zone_colors_list[:len(zone_labels)],
            text=[_fmt_duration(s) for s in zone_seconds],
            textposition="auto",
            textfont=dict(color="#FAFAFA", size=10),
        ))
        fig_hr.update_layout(
            plot_bgcolor="#1A1D23",
            paper_bgcolor="#1A1D23",
            font_color="#FAFAFA",
            margin=dict(l=60, r=20, t=20, b=30),
            height=200,
            xaxis=dict(title="Time (seconds)", gridcolor="#2D3139"),
            yaxis=dict(gridcolor="#2D3139"),
            bargap=0.3,
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
                        st.session_state.page = "app"
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

    if st.button("Logout", use_container_width=True):
        _logout()
        st.rerun()

    st.markdown("---")

    # Garmin connection card
    st.markdown('<div class="pf-garmin-card">', unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.8rem;font-weight:600;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#8B92A5;margin-bottom:0.5rem;">Garmin Connect</p>',
        unsafe_allow_html=True,
    )

    if not st.session_state.garmin_logged_in:
        if not st.session_state.mfa_required:
            garmin_email = st.text_input("Garmin Email", key="garmin_email_input")
            garmin_password = st.text_input("Garmin Password", type="password", key="garmin_pw_input")
            if st.button("Connect", type="primary", use_container_width=True, key="garmin_connect_btn"):
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
            mfa_code = st.text_input("MFA Code", placeholder="123456", key="mfa_input")
            if st.button("Verify", type="primary", use_container_width=True, key="mfa_btn"):
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
            '<div class="pf-garmin-connected">Connected</div>',
            unsafe_allow_html=True,
        )
        if st.button("Refresh Profile", use_container_width=True, key="refresh_profile_btn"):
            r = requests.get(f"{API_BASE}/profile", headers=_auth_headers(), timeout=30)
            if r.status_code == 200:
                st.session_state.profile = r.json()

    st.markdown('</div>', unsafe_allow_html=True)


# ── Tabs ─────────────────────────────────────────────────────────────

tab_names = ["Fitness Profile", "Training Plan", "Calendar", "Push to Garmin", "AI Coach"]
if st.session_state.role == "admin":
    tab_names.append("Admin Panel")

tabs = st.tabs(tab_names)
tab_profile = tabs[0]
tab_plan = tabs[1]
tab_calendar = tabs[2]
tab_push = tabs[3]
tab_coach = tabs[4]
tab_admin = tabs[5] if st.session_state.role == "admin" else None


# ── Tab 1: Fitness Profile ───────────────────────────────────────────

with tab_profile:
    if not st.session_state.garmin_logged_in:
        st.info("Connect to Garmin using the sidebar to load your profile.")
    else:
        if st.button("Load Fitness Profile", type="primary", key="load_profile_btn"):
            with st.spinner("Fetching from Garmin Connect..."):
                r = requests.get(f"{API_BASE}/profile", headers=_auth_headers(), timeout=60)
                if r.status_code == 200:
                    st.session_state.profile = r.json()
                else:
                    st.error("Failed to fetch profile")

        p = st.session_state.profile
        if p:
            # ── KPI Metric Cards ──
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(
                    _metric_card("VO2 Max", str(p.get("vo2_max", "—")), "", "green"),
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    _metric_card("Resting HR", str(p.get("resting_hr", "—")), "bpm", "blue"),
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    _metric_card("Training Readiness", str(p.get("training_readiness", "—")), "", "orange"),
                    unsafe_allow_html=True,
                )
            with c4:
                st.markdown(
                    _metric_card("HRV Status", str(p.get("hrv_status", "—")), "", "purple"),
                    unsafe_allow_html=True,
                )

            st.markdown("")

            # ── Gauges with Plotly ──
            try:
                import plotly.graph_objects as go

                gauge_col1, gauge_col2 = st.columns(2)

                vo2 = p.get("vo2_max")
                if vo2 and isinstance(vo2, (int, float)):
                    fig_vo2 = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=vo2,
                        title={"text": "VO2 Max", "font": {"size": 16, "color": "#8B92A5"}},
                        number={"font": {"size": 42, "color": "#FAFAFA"}},
                        gauge={
                            "axis": {"range": [20, 70], "tickcolor": "#3A3F4B", "tickfont": {"color": "#8B92A5"}},
                            "bar": {"color": "#00D26A"},
                            "bgcolor": "#2D3139",
                            "borderwidth": 0,
                            "steps": [
                                {"range": [20, 35], "color": "rgba(244,67,54,0.15)"},
                                {"range": [35, 50], "color": "rgba(255,152,0,0.15)"},
                                {"range": [50, 70], "color": "rgba(0,210,106,0.15)"},
                            ],
                        },
                    ))
                    fig_vo2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=250,
                        margin=dict(t=40, b=20, l=30, r=30),
                    )
                    with gauge_col1:
                        st.plotly_chart(fig_vo2, use_container_width=True, key="gauge_vo2")

                readiness = p.get("training_readiness")
                if readiness and isinstance(readiness, (int, float)):
                    fig_tr = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=readiness,
                        title={"text": "Training Readiness", "font": {"size": 16, "color": "#8B92A5"}},
                        number={"font": {"size": 42, "color": "#FAFAFA"}},
                        gauge={
                            "axis": {"range": [0, 100], "tickcolor": "#3A3F4B", "tickfont": {"color": "#8B92A5"}},
                            "bar": {"color": "#FF9800"},
                            "bgcolor": "#2D3139",
                            "borderwidth": 0,
                            "steps": [
                                {"range": [0, 33], "color": "rgba(244,67,54,0.15)"},
                                {"range": [33, 66], "color": "rgba(255,152,0,0.15)"},
                                {"range": [66, 100], "color": "rgba(0,210,106,0.15)"},
                            ],
                        },
                    ))
                    fig_tr.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=250,
                        margin=dict(t=40, b=20, l=30, r=30),
                    )
                    with gauge_col2:
                        st.plotly_chart(fig_tr, use_container_width=True, key="gauge_readiness")
            except ImportError:
                pass

            st.markdown("")

            # ── Race Predictions + Weekly Mileage ──
            pred_col, mile_col = st.columns(2)

            with pred_col:
                st.markdown('<div class="pf-section-header">Race Predictions</div>', unsafe_allow_html=True)
                preds = p.get("race_predictions", [])
                if preds:
                    for pred in preds:
                        secs = pred["predicted_seconds"]
                        h = int(secs) // 3600
                        m = (int(secs) % 3600) // 60
                        s = int(secs) % 60
                        time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                        st.markdown(
                            f"""<div style="display:flex;justify-content:space-between;
                            padding:0.5rem 0;border-bottom:1px solid #2D3139;">
                                <span style="font-weight:500;">{pred['distance']}</span>
                                <span style="color:#00D26A;font-weight:600;">{time_str}</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown('<p style="color:#8B92A5;">No race predictions available</p>', unsafe_allow_html=True)

            with mile_col:
                st.markdown('<div class="pf-section-header">Weekly Mileage</div>', unsafe_allow_html=True)
                km = p.get("weekly_mileage_km", 0)
                st.markdown(
                    _metric_card("Last 30 Days", str(km), "km/week", "cyan"),
                    unsafe_allow_html=True,
                )

            st.markdown("")

            # ── Recent Activities ──
            st.markdown('<div class="pf-section-header">Recent Activities</div>', unsafe_allow_html=True)
            acts = p.get("recent_activities", [])
            if acts:
                st.markdown('<div class="pf-card">', unsafe_allow_html=True)
                for a in acts[:10]:
                    dist = round(a.get("distance_meters", 0) / 1000, 1)
                    pace = a.get("avg_pace_sec_per_km")
                    pace_str = ""
                    if pace:
                        pm, ps = divmod(int(pace), 60)
                        pace_str = f"{pm}:{ps:02d}/km"
                    st.markdown(
                        f"""<div class="pf-activity-row">
                            <span class="pf-activity-name">{a['name']}</span>
                            <span class="pf-activity-dist">{dist} km</span>
                            <span class="pf-activity-pace">{pace_str}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="color:#8B92A5;text-align:center;margin-top:3rem;">Click <b>Load Fitness Profile</b> to view your data.</p>',
                unsafe_allow_html=True,
            )


# ── Tab 2: Training Plan ─────────────────────────────────────────────

with tab_plan:
    if not st.session_state.garmin_logged_in:
        st.info("Connect to Garmin first to generate a plan.")
    else:
        st.markdown('<div class="pf-section-header">Generate a Training Plan</div>', unsafe_allow_html=True)

        # Form in card
        st.markdown('<div class="pf-card">', unsafe_allow_html=True)
        goal_type = st.selectbox(
            "Goal",
            ["HALF_MARATHON", "MARATHON", "HYROX", "5K", "10K"],
        )
        target_date = st.date_input(
            "Race Date",
            value=date.today() + timedelta(weeks=14),
            min_value=date.today() + timedelta(weeks=6),
        )

        col1, col2 = st.columns(2)
        with col1:
            target_time_h = st.number_input("Target time — hours", 0, 6, 1)
            target_time_m = st.number_input("Target time — minutes", 0, 59, 45)
        with col2:
            experience = st.selectbox("Experience Level", ["intermediate", "beginner", "advanced"])

        ALL_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        DAY_LABELS = {d: d.capitalize() for d in ALL_DAYS}

        training_days = st.multiselect(
            "Training Days",
            options=ALL_DAYS,
            default=["tuesday", "wednesday", "thursday", "saturday", "sunday"],
            format_func=lambda d: DAY_LABELS[d],
        )
        if len(training_days) < 3:
            st.warning("Select at least 3 training days.")

        long_run_day = st.selectbox(
            "Long Run Day",
            options=training_days if training_days else ["sunday"],
            index=len(training_days) - 1 if training_days else 0,
            format_func=lambda d: DAY_LABELS.get(d, d),
        )

        target_secs = (target_time_h * 3600 + target_time_m * 60) if (target_time_h + target_time_m) > 0 else None
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Generate Plan", type="primary", use_container_width=True) and len(training_days) >= 3:
            with st.spinner("Building your personalized plan..."):
                r = requests.post(
                    f"{API_BASE}/plan/generate",
                    json={
                        "goal_type": goal_type,
                        "target_date": str(target_date),
                        "target_time_seconds": target_secs,
                        "experience_level": experience,
                        "training_days": training_days,
                        "long_run_day": long_run_day,
                    },
                    headers=_auth_headers(),
                    timeout=30,
                )
                if r.status_code == 200:
                    st.session_state.plan = r.json()
                    st.success("Plan generated!")
                else:
                    st.error(f"Error: {_error_detail(r)}")

        plan = st.session_state.plan
        if plan:
            st.markdown("---")
            st.markdown(
                f'<div class="pf-section-header">{plan["name"]}</div>',
                unsafe_allow_html=True,
            )

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
                            f"""<div class="pf-pace-card">
                                <div class="pf-pace-zone" style="color:{color};">{zone}</div>
                                <div class="pf-pace-value">{val}<span class="pf-metric-unit">/km</span></div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

            st.markdown("")

            # ── Weekly Breakdown ──
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
                        f"""<div class="pf-week-header">
                            <span class="pf-week-phase" style="background:{phase_bg};color:{phase_color};">
                                {phase}
                            </span>
                            <span class="pf-week-meta">{total_km} km total</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    for w in week.get("workouts", []):
                        wtype = w.get("workout_type", "rest")
                        color = _WORKOUT_COLORS.get(wtype, "#607D8B")

                        if wtype == "rest":
                            st.markdown(
                                f"""<div class="pf-workout-item">
                                    <div class="pf-workout-dot" style="background:#9E9E9E;"></div>
                                    <div class="pf-workout-info">
                                        <div class="pf-workout-name" style="color:#8B92A5;">
                                            {w.get('scheduled_date', '')} — Rest Day
                                        </div>
                                    </div>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                        else:
                            dist = round(w.get("estimated_distance_meters", 0) / 1000, 1)
                            purpose = w.get("purpose", "")
                            notes = w.get("notes", "")
                            detail_parts = [f"{dist} km"]
                            if purpose:
                                detail_parts.append(purpose)
                            if notes:
                                detail_parts.append(notes)
                            detail = " · ".join(detail_parts)

                            st.markdown(
                                f"""<div class="pf-workout-item">
                                    <div class="pf-workout-dot" style="background:{color};"></div>
                                    <div class="pf-workout-info">
                                        <div class="pf-workout-name">
                                            {w.get('scheduled_date', '')} — {w['name']}
                                        </div>
                                        <div class="pf-workout-detail">{detail}</div>
                                    </div>
                                </div>""",
                                unsafe_allow_html=True,
                            )

            st.markdown("")
            if st.button("Adapt Plan (re-evaluate)", use_container_width=True):
                with st.spinner("Adapting plan based on latest fitness..."):
                    r = requests.post(
                        f"{API_BASE}/plan/adapt",
                        headers=_auth_headers(),
                        timeout=30,
                    )
                    if r.status_code == 200:
                        st.session_state.plan = r.json()
                        st.success("Plan adapted!")
                        st.rerun()
                    else:
                        st.error(f"Error: {_error_detail(r)}")


# ── Tab 3: Calendar ──────────────────────────────────────────────────

with tab_calendar:
    st.markdown('<div class="pf-section-header">Training Calendar</div>', unsafe_allow_html=True)

    if not st.session_state.garmin_logged_in:
        st.info("Connect to Garmin using the sidebar to view your activities.")
    else:
        # Fetch Garmin activities
        if st.button("Sync Activities from Garmin", type="primary", key="sync_activities_btn"):
            with st.spinner("Fetching activities from Garmin Connect..."):
                try:
                    r = requests.get(
                        f"{API_BASE}/activities?days=90",
                        headers=_auth_headers(),
                        timeout=60,
                    )
                    if r.status_code == 200:
                        st.session_state["garmin_activities"] = r.json()
                        st.success(f"Synced {len(r.json())} activities!")
                    else:
                        st.error(f"Failed to sync: {_error_detail(r)}")
                except requests.ConnectionError:
                    st.error("Cannot reach API.")

        cal_events = []

        # ── Past activities from Garmin ──
        garmin_acts = st.session_state.get("garmin_activities", [])
        for i, act in enumerate(garmin_acts):
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

        # ── Planned workouts from generated plan ──
        plan = st.session_state.plan
        if plan:
            for week in plan.get("weeks", []):
                for j, w in enumerate(week.get("workouts", [])):
                    wtype = w.get("workout_type", "rest")
                    if wtype == "rest":
                        continue
                    dist = round(w.get("estimated_distance_meters", 0) / 1000, 1)
                    cal_events.append({
                        "id": f"plan_w{week['week_number']}_{j}",
                        "title": f"📋 {w['name']} ({dist}km)",
                        "start": w.get("scheduled_date", ""),
                        "allDay": True,
                        "backgroundColor": _WORKOUT_COLORS.get(wtype, "#607D8B"),
                        "borderColor": _WORKOUT_COLORS.get(wtype, "#607D8B"),
                        "editable": True,
                        "extendedProps": {
                            "source": "plan",
                            "workout_type": wtype,
                            "purpose": w.get("purpose", ""),
                            "name": w["name"],
                            "steps": json.dumps(w.get("steps", [])),
                            "notes": w.get("notes", ""),
                            "estimated_distance_meters": w.get("estimated_distance_meters", 0),
                            "estimated_duration_seconds": w.get("estimated_duration_seconds", 0),
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
            # Legend
            st.markdown(
                '<div style="display:flex;gap:1.5rem;margin-bottom:0.75rem;font-size:0.8rem;">'
                '<span style="color:#00D26A;">● Completed (Garmin)</span>'
                '<span style="color:#2196F3;">● Planned (Long Run)</span>'
                '<span style="color:#4CAF50;">● Planned (Easy)</span>'
                '<span style="color:#FF9800;">● Planned (Tempo)</span>'
                '<span style="color:#F44336;">● Planned (Speed)</span>'
                '</div>',
                unsafe_allow_html=True,
            )

            if plan:
                st.caption("Drag planned workouts (📋) to reschedule them.")

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
            }

            cal_css = """
                .fc { background: #1A1D23; color: #FAFAFA; border: none; }
                .fc-theme-standard td, .fc-theme-standard th { border-color: #2D3139; }
                .fc-theme-standard .fc-scrollgrid { border-color: #2D3139; }
                .fc-col-header-cell { background: #242830; }
                .fc-col-header-cell-cushion { color: #8B92A5; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }
                .fc-daygrid-day-number { color: #8B92A5; font-size: 0.85rem; }
                .fc-day-today { background: rgba(0,210,106,0.06) !important; }
                .fc-event { cursor: grab; font-size: 0.8em; border-radius: 6px; padding: 2px 6px; border: none !important; }
                .fc-event-title { font-weight: 600; }
                .fc-button { background: #242830 !important; border: 1px solid #3A3F4B !important; color: #FAFAFA !important; font-size: 0.85rem !important; }
                .fc-button:hover { background: #2D3139 !important; }
                .fc-button-active { background: #00D26A !important; color: #1A1D23 !important; border-color: #00D26A !important; }
                .fc-toolbar-title { font-size: 1.1rem !important; font-weight: 700; color: #FAFAFA; }
            """

            from streamlit_calendar import calendar as st_calendar

            result = st_calendar(
                events=cal_events,
                options=cal_options,
                custom_css=cal_css,
                key="plan_calendar",
            )

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
                        st.success(f"Moved to {new_start[:10]}")
                    else:
                        st.error("Failed to reschedule")

            if result and result.get("callback") == "eventClick":
                ev_data = result["eventClick"]["event"]
                props = ev_data.get("extendedProps", {})
                if props.get("source") == "garmin":
                    activity_id = props.get("activity_id")
                    st.markdown(
                        f'<div style="font-weight:700;font-size:1.1rem;margin:1rem 0 0.5rem;">✓ {ev_data.get("title", "Activity")}</div>'
                        f'<div style="color:#8B92A5;font-size:0.85rem;margin-bottom:0.5rem;">Date: {ev_data.get("start", "")[:10]}</div>',
                        unsafe_allow_html=True,
                    )
                    if activity_id:
                        with st.spinner("Loading activity details..."):
                            try:
                                r = requests.get(
                                    f"{API_BASE}/activities/{activity_id}",
                                    headers=_auth_headers(),
                                    timeout=30,
                                )
                                if r.status_code == 200:
                                    _render_garmin_activity_detail(r.json())
                                else:
                                    st.warning(f"Could not load details: {_error_detail(r)}")
                            except requests.ConnectionError:
                                st.error("Cannot reach API.")
                    else:
                        # Fallback for activities without an ID
                        dur = props.get("duration_seconds", 0)
                        dur_m, dur_s = divmod(int(dur), 60)
                        hr_text = f" · Avg HR: {props['avg_hr']} bpm" if props.get("avg_hr") else ""
                        st.markdown(
                            f'<div class="pf-card"><span style="color:#8B92A5;">Duration: {dur_m}:{dur_s:02d}{hr_text}</span></div>',
                            unsafe_allow_html=True,
                        )
                else:
                    # Planned workout — render structured description
                    steps_json = props.get("steps", "[]")
                    try:
                        steps_list = json.loads(steps_json) if isinstance(steps_json, str) else steps_json
                    except (json.JSONDecodeError, TypeError):
                        steps_list = []
                    workout_dict = {
                        "name": props.get("name", ev_data.get("title", "Workout")),
                        "workout_type": props.get("workout_type", ""),
                        "purpose": props.get("purpose", ""),
                        "notes": props.get("notes", ""),
                        "steps": steps_list,
                        "estimated_distance_meters": props.get("estimated_distance_meters", 0),
                        "estimated_duration_seconds": props.get("estimated_duration_seconds", 0),
                    }
                    plan_paces = None
                    if st.session_state.plan:
                        plan_paces = {
                            k: st.session_state.plan.get(k)
                            for k in ("easy_pace", "marathon_pace", "threshold_pace", "interval_pace", "repetition_pace")
                        }
                    st.markdown(
                        _render_workout_detail(workout_dict, plan_paces),
                        unsafe_allow_html=True,
                    )


# ── Tab 4: Push to Garmin ────────────────────────────────────────────

with tab_push:
    plan = st.session_state.plan
    if not plan:
        st.info("Generate a plan first.")
    elif not st.session_state.garmin_logged_in:
        st.info("Connect to Garmin first.")
    else:
        st.markdown('<div class="pf-section-header">Push Workouts to Garmin</div>', unsafe_allow_html=True)
        st.markdown(
            '<p style="color:#8B92A5;margin-bottom:1rem;">Select which weeks to push to your Garmin calendar.</p>',
            unsafe_allow_html=True,
        )

        week_options = [f"Week {w['week_number']} — {w['phase']}" for w in plan.get("weeks", [])]
        selected = st.multiselect("Weeks", week_options)

        if st.button("Push Selected Weeks", type="primary", use_container_width=True):
            week_nums = [int(s.split()[1]) for s in selected]
            with st.spinner("Pushing workouts to Garmin Connect..."):
                r = requests.post(
                    f"{API_BASE}/plan/push",
                    json={"week_numbers": week_nums},
                    headers=_auth_headers(),
                    timeout=120,
                )
                if r.status_code == 200:
                    try:
                        data = r.json()
                        st.success(f"Pushed {data['workouts_pushed']} workouts to Garmin Connect!")
                    except Exception:
                        st.success("Workouts pushed to Garmin Connect!")
                else:
                    st.error(f"Error: {_error_detail(r)}")


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


# ── Tab 6: Admin Panel ──────────────────────────────────────────────

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
