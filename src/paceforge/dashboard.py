"""PaceForge — Streamlit Dashboard (Dark Modern UI)."""

from __future__ import annotations

import base64
import json
import logging
import time
from datetime import date, timedelta
from datetime import datetime as _dt_now
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
/* ── Design System ───────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Figtree:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --pf-bg: #0F1117;
    --pf-surface: #161821;
    --pf-elevated: #1C1F2B;
    --pf-card: #1A1D2B;
    --pf-border-subtle: rgba(148, 163, 194, 0.08);
    --pf-border: rgba(148, 163, 194, 0.12);
    --pf-border-strong: rgba(148, 163, 194, 0.18);
    --pf-text: #E8ECF4;
    --pf-text-secondary: #8B95AD;
    --pf-text-tertiary: #5C6478;
    --pf-emerald: #10B981;
    --pf-emerald-dim: rgba(16, 185, 129, 0.12);
    --pf-emerald-glow: rgba(16, 185, 129, 0.06);
    --pf-amber: #F59E0B;
    --pf-amber-dim: rgba(245, 158, 11, 0.12);
    --pf-sky: #0EA5E9;
    --pf-sky-dim: rgba(14, 165, 233, 0.12);
    --pf-rose: #F43F5E;
    --pf-rose-dim: rgba(244, 63, 94, 0.12);
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;
    --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
    --duration-fast: 150ms;
    --duration-base: 200ms;
    --font-display: 'Manrope', sans-serif;
    --font-body: 'Figtree', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
}

/* ── Global ──────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--font-body);
    -webkit-font-smoothing: antialiased;
}

.block-container {
    padding-top: var(--space-xl) !important;
    padding-bottom: var(--space-xl) !important;
    max-width: 1200px;
}

/* ── Cards ───────────────────────────────────────────── */
.pf-card {
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
    border-radius: 12px;
    padding: var(--space-lg);
    margin-bottom: var(--space-md);
    transition: border-color var(--duration-fast) var(--ease-out),
                transform var(--duration-fast) var(--ease-out);
}
.pf-card:hover {
    border-color: var(--pf-border-strong);
    transform: translateY(-1px);
}

/* ── Metric cards (clean — no top bar) ───────────────── */
.pf-metric-card {
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    transition: border-color var(--duration-fast) var(--ease-out),
                transform var(--duration-fast) var(--ease-out);
}
.pf-metric-card:hover {
    border-color: var(--pf-border-strong);
    transform: translateY(-1px);
}
.pf-metric-label {
    font-family: var(--font-body);
    font-size: 0.72rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--pf-text-tertiary);
    margin-bottom: 0.4rem;
}
.pf-metric-value {
    font-family: var(--font-mono);
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--pf-text);
    line-height: 1.1;
}
.pf-metric-unit {
    font-family: var(--font-body);
    font-size: 0.8rem;
    font-weight: 400;
    color: var(--pf-text-tertiary);
    margin-left: 0.15rem;
}

/* ── Indicator dots ──────────────────────────────────── */
.pf-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
    flex-shrink: 0;
}
.pf-dot-emerald { background: var(--pf-emerald); }
.pf-dot-sky { background: var(--pf-sky); }
.pf-dot-amber { background: var(--pf-amber); }
.pf-dot-rose { background: var(--pf-rose); }
.pf-dot-muted { background: var(--pf-text-tertiary); }

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
    font-family: var(--font-display);
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--pf-text);
}
.pf-brand-text span {
    color: var(--pf-emerald);
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
    font-family: var(--font-display);
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0;
    color: var(--pf-text);
}
.pf-auth-header h1 span {
    color: var(--pf-emerald);
}
.pf-auth-header p {
    color: var(--pf-text-secondary);
    font-size: 0.9rem;
    margin-top: 0.5rem;
}

/* ── Sidebar ─────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--pf-surface) !important;
    border-right: 1px solid var(--pf-border-subtle);
}
section[data-testid="stSidebar"] .pf-user-badge {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: var(--pf-elevated);
    border-radius: 10px;
    border: 1px solid var(--pf-border-subtle);
    margin-bottom: 1rem;
}
.pf-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--pf-emerald), #059669);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1rem;
    flex-shrink: 0;
}
.pf-user-name {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--pf-text);
}
.pf-user-role {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--pf-text-tertiary);
}
.pf-garmin-card {
    background: var(--pf-elevated);
    border: 1px solid var(--pf-border-subtle);
    border-radius: 10px;
    padding: 1rem;
    margin-top: 0.5rem;
}
.pf-garmin-connected {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--pf-emerald);
    font-weight: 600;
    font-size: 0.85rem;
}
.pf-garmin-connected::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--pf-emerald);
    box-shadow: 0 0 6px var(--pf-emerald);
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background: var(--pf-emerald) !important;
    color: #fff !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.5rem !important;
    transition: all var(--duration-fast) var(--ease-out) !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    background: #059669 !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"]:active,
.stFormSubmitButton > button[kind="primary"]:active {
    transform: scale(0.97);
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid var(--pf-border-strong) !important;
    border-radius: 8px !important;
    color: var(--pf-text) !important;
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
    transition: all var(--duration-fast) var(--ease-out) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--pf-emerald) !important;
    color: var(--pf-emerald) !important;
}

/* ── Tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--pf-border);
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent;
    padding: 0.75rem 1.25rem !important;
    font-family: var(--font-body);
    font-weight: 500;
    color: var(--pf-text-secondary) !important;
    transition: all var(--duration-fast) var(--ease-out);
}
.stTabs [aria-selected="true"] {
    border-bottom-color: var(--pf-emerald) !important;
    color: var(--pf-text) !important;
    font-weight: 600;
}

/* ── Inputs ──────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: var(--pf-bg) !important;
    border: 1px solid var(--pf-border) !important;
    border-radius: 8px !important;
    color: var(--pf-text) !important;
    font-family: var(--font-body) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--pf-emerald) !important;
    box-shadow: 0 0 0 1px var(--pf-emerald) !important;
}

/* ── Status badges ───────────────────────────────────── */
.pf-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-family: var(--font-body);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.pf-badge.pending { background: var(--pf-amber-dim); color: var(--pf-amber); }
.pf-badge.approved { background: var(--pf-emerald-dim); color: var(--pf-emerald); }
.pf-badge.rejected { background: var(--pf-rose-dim); color: var(--pf-rose); }
.pf-badge.admin { background: var(--pf-emerald-dim); color: var(--pf-emerald); }

/* ── Workout pills ───────────────────────────────────── */
.pf-workout-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.75rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 0.2rem 0.2rem 0.2rem 0;
}

/* ── Training pace cards ─────────────────────────────── */
.pf-pace-card {
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    text-align: center;
}
.pf-pace-zone {
    font-family: var(--font-body);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.3rem;
}
.pf-pace-value {
    font-family: var(--font-mono);
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--pf-text);
}

/* ── Coach chat ──────────────────────────────────────── */
.pf-chat-bubble {
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
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
    border-bottom: 1px solid var(--pf-border-subtle);
    font-size: 0.85rem;
}
.pf-activity-row:last-child { border-bottom: none; }
.pf-activity-name { flex: 2; font-weight: 500; color: var(--pf-text); }
.pf-activity-dist { flex: 1; color: var(--pf-text-secondary); text-align: right; }
.pf-activity-pace { flex: 1; color: var(--pf-emerald); text-align: right; font-family: var(--font-mono); font-weight: 600; }

/* ── Week cards ──────────────────────────────────────── */
.pf-week-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
}
.pf-week-title {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1rem;
    color: var(--pf-text);
}
.pf-week-meta {
    font-size: 0.8rem;
    color: var(--pf-text-secondary);
}
.pf-week-phase {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: var(--pf-emerald-dim);
    color: var(--pf-emerald);
}
.pf-workout-item {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--pf-border-subtle);
    transition: background var(--duration-fast) ease;
    border-radius: 6px;
    padding-left: 6px;
    margin-left: -6px;
}
.pf-workout-item:hover {
    background: var(--pf-elevated);
}
.pf-workout-item:last-child { border-bottom: none; }
.pf-workout-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-top: 0.4rem;
    flex-shrink: 0;
}
.pf-workout-info { flex: 1; }
.pf-workout-name { font-weight: 600; font-size: 0.88rem; color: var(--pf-text); }
.pf-workout-detail { font-size: 0.78rem; color: var(--pf-text-secondary); margin-top: 0.15rem; }

/* ── User cards (admin) ──────────────────────────────── */
.pf-user-card {
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
    border-radius: 10px;
    padding: 1.2rem;
    margin-bottom: 0.75rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* ── Section headers ─────────────────────────────────── */
.pf-section-header {
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--pf-text);
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--pf-border-subtle);
}

/* ── Scrollbar ───────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--pf-bg); }
::-webkit-scrollbar-thumb { background: var(--pf-border-strong); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--pf-text-tertiary); }

/* ── Misc polish ─────────────────────────────────────── */
.stDivider { border-color: var(--pf-border) !important; }
hr { border-color: var(--pf-border) !important; }

/* ── Metrics strip (divide-x) ────────────────────────── */
.pf-metrics-strip {
    display: flex;
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: var(--space-md);
}
.pf-metrics-strip > .pf-ms-item {
    flex: 1;
    padding: 14px 12px;
    text-align: center;
    border-right: 1px solid var(--pf-border-subtle);
    min-width: 0;
    transition: background var(--duration-fast) ease;
}
.pf-metrics-strip > .pf-ms-item:hover {
    background: var(--pf-elevated);
}
.pf-metrics-strip > .pf-ms-item:last-child {
    border-right: none;
}
.pf-ms-label {
    font-family: var(--font-body);
    font-size: 0.68rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--pf-text-tertiary);
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.pf-ms-value {
    font-family: var(--font-mono);
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--pf-text);
    line-height: 1.2;
}
.pf-ms-unit {
    font-family: var(--font-body);
    font-size: 0.7rem;
    font-weight: 400;
    color: var(--pf-text-tertiary);
    margin-left: 2px;
}

/* ── Splits table ────────────────────────────────────── */
.pf-splits-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
    font-family: var(--font-body);
}
.pf-splits-table thead th {
    color: var(--pf-text-tertiary);
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 6px 8px;
    text-align: center;
    border-bottom: 1px solid var(--pf-border);
}
.pf-splits-table thead th:first-child { text-align: left; }
.pf-splits-table tbody td {
    padding: 7px 8px;
    text-align: center;
    color: var(--pf-text);
    border-bottom: 1px solid var(--pf-border-subtle);
    transition: background var(--duration-fast) ease;
}
.pf-splits-table tbody tr:hover td {
    background: var(--pf-elevated);
}
.pf-splits-table tbody td:first-child {
    text-align: left;
    font-weight: 600;
    font-family: var(--font-mono);
    color: var(--pf-text-tertiary);
}
.pf-splits-table .pf-pace-cell {
    font-family: var(--font-mono);
    font-weight: 600;
    position: relative;
}
.pf-pace-bar {
    position: absolute;
    bottom: 0; left: 4px; right: 4px;
    height: 3px;
    border-radius: 1.5px;
    opacity: 0.5;
}

/* ── HR zone bars (CSS-only) ─────────────────────────── */
.pf-hz-bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
}
.pf-hz-label {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    width: 32px;
    flex-shrink: 0;
    text-align: right;
}
.pf-hz-track {
    flex: 1;
    height: 16px;
    background: var(--pf-border-subtle);
    border-radius: 3px;
    overflow: hidden;
    position: relative;
}
.pf-hz-fill {
    height: 100%;
    border-radius: 3px;
    display: flex;
    align-items: center;
    padding-left: 6px;
    min-width: 0;
    animation: pf-hz-grow 600ms var(--ease-out) both;
}
@keyframes pf-hz-grow {
    from { transform: scaleX(0); transform-origin: left; }
    to { transform: scaleX(1); transform-origin: left; }
}
.pf-hz-bar-row:nth-child(2) .pf-hz-fill { animation-delay: 50ms; }
.pf-hz-bar-row:nth-child(3) .pf-hz-fill { animation-delay: 100ms; }
.pf-hz-bar-row:nth-child(4) .pf-hz-fill { animation-delay: 150ms; }
.pf-hz-bar-row:nth-child(5) .pf-hz-fill { animation-delay: 200ms; }
.pf-hz-time {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    font-weight: 500;
    color: rgba(255,255,255,0.85);
    white-space: nowrap;
}

/* ── Workout day dots ────────────────────────────────── */
.pf-day-dots {
    display: flex;
    gap: 3px;
    margin-top: 4px;
}
.pf-day-letter {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 0.6rem;
    font-weight: 600;
    color: var(--pf-text-tertiary);
    background: var(--pf-border-subtle);
}
.pf-day-letter.active {
    background: currentColor;
    color: var(--pf-bg);
}

/* Hide Streamlit default header/footer */
#MainMenu { visibility: hidden; }
header { visibility: hidden; }
footer { visibility: hidden; }

/* ── Loading overlay ─────────────────────────────────── */
[data-testid="stAppViewContainer"][data-stale="true"]::after {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 17, 23, 0.65);
    z-index: 99998;
    pointer-events: all;
    animation: pf-fade-in 150ms ease-out;
}
@keyframes pf-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
}
[data-testid="stAppViewContainer"][data-stale="true"]::before {
    content: '';
    position: fixed;
    top: 50%; left: 50%;
    margin-top: -16px; margin-left: -16px;
    width: 32px; height: 32px;
    border: 3px solid var(--pf-border-strong);
    border-top-color: var(--pf-emerald);
    border-radius: 50%;
    z-index: 99999;
    animation: pf-spin 0.7s linear infinite;
}
@keyframes pf-spin {
    to { transform: rotate(360deg); }
}

/* ── Mobile Responsive ───────────────────────────────── */
@media (max-width: 768px) {
    .block-container {
        padding-top: var(--space-md) !important;
        padding-bottom: var(--space-md) !important;
        padding-left: var(--space-sm) !important;
        padding-right: var(--space-sm) !important;
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

/* ── Staggered fade-in ───────────────────────────────── */
@keyframes pf-fade-up {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
.pf-metrics-strip > .pf-ms-item {
    animation: pf-fade-up 400ms var(--ease-out) both;
}
.pf-metrics-strip > .pf-ms-item:nth-child(1) { animation-delay: 0ms; }
.pf-metrics-strip > .pf-ms-item:nth-child(2) { animation-delay: 40ms; }
.pf-metrics-strip > .pf-ms-item:nth-child(3) { animation-delay: 80ms; }
.pf-metrics-strip > .pf-ms-item:nth-child(4) { animation-delay: 120ms; }
.pf-metrics-strip > .pf-ms-item:nth-child(5) { animation-delay: 160ms; }
.pf-metrics-strip > .pf-ms-item:nth-child(n+6) { animation-delay: 200ms; }

.pf-workout-item {
    animation: pf-fade-up 300ms var(--ease-out) both;
}

/* ── Pace bar grow animation ─────────────────────────── */
@keyframes pf-bar-grow {
    from { transform: scaleX(0); }
    to { transform: scaleX(1); }
}
.pf-pace-bar {
    transform-origin: left;
    animation: pf-bar-grow 500ms var(--ease-out) 200ms both;
}

/* ── Skeleton loading ────────────────────────────────── */
@keyframes pf-shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.pf-skeleton {
    background: linear-gradient(
        90deg,
        var(--pf-border-subtle) 25%,
        rgba(148, 163, 194, 0.12) 50%,
        var(--pf-border-subtle) 75%
    );
    background-size: 200% 100%;
    animation: pf-shimmer 1.5s linear infinite;
    border-radius: 6px;
}
.pf-skeleton-text {
    height: 14px;
    width: 80%;
    margin-bottom: 8px;
}
.pf-skeleton-value {
    height: 28px;
    width: 60%;
    margin: 0 auto;
}
.pf-skeleton-card {
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}

/* ── Tab indicator transition ────────────────────────── */
.stTabs [data-baseweb="tab"] {
    transition: color var(--duration-fast) var(--ease-out),
                border-color var(--duration-base) var(--ease-out) !important;
}

/* ── Expander open animation ─────────────────────────── */
details[open] > div {
    animation: pf-fade-up 250ms var(--ease-out);
}

/* ── Day dot entrance ────────────────────────────────── */
.pf-day-letter {
    animation: pf-fade-up 250ms var(--ease-out) both;
}
.pf-day-dots .pf-day-letter:nth-child(1) { animation-delay: 0ms; }
.pf-day-dots .pf-day-letter:nth-child(2) { animation-delay: 30ms; }
.pf-day-dots .pf-day-letter:nth-child(3) { animation-delay: 60ms; }
.pf-day-dots .pf-day-letter:nth-child(4) { animation-delay: 90ms; }
.pf-day-dots .pf-day-letter:nth-child(5) { animation-delay: 120ms; }
.pf-day-dots .pf-day-letter:nth-child(6) { animation-delay: 150ms; }
.pf-day-dots .pf-day-letter:nth-child(7) { animation-delay: 180ms; }

/* ── Button active feedback (all buttons) ────────────── */
.stButton > button:active {
    transform: scale(0.97) !important;
    transition: transform 100ms var(--ease-out) !important;
}

/* ── Auth page ───────────────────────────────────────── */
.pf-auth-container {
    max-width: 420px;
    margin: 0 auto;
    padding: 2.5rem 0;
}
.pf-auth-hero {
    text-align: center;
    margin-bottom: var(--space-xl);
}
.pf-auth-hero img {
    width: 64px;
    height: 64px;
    margin-bottom: var(--space-md);
}
.pf-auth-title {
    font-family: var(--font-display);
    font-size: 1.75rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--pf-text);
    margin: 0 0 var(--space-xs) 0;
}
.pf-auth-title span {
    color: var(--pf-emerald);
}
.pf-auth-subtitle {
    color: var(--pf-text-secondary);
    font-family: var(--font-body);
    font-size: 0.9rem;
    margin: 0;
}
.pf-auth-form {
    background: var(--pf-card);
    border: 1px solid var(--pf-border);
    border-radius: 14px;
    padding: var(--space-lg) var(--space-xl);
}
.pf-auth-form h4 {
    font-family: var(--font-display);
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: var(--space-md);
}
.pf-auth-footer {
    text-align: center;
    margin-top: var(--space-md);
    color: var(--pf-text-tertiary);
    font-size: 0.8rem;
    font-family: var(--font-body);
}
</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# ── Count-up animation for metric values ──
_COUNTUP_JS = """
<script>
(function() {
    if (window._pfCountUp) return;
    window._pfCountUp = true;
    function countUp(el) {
        var text = el.textContent.trim();
        var match = text.match(/^([\\d.]+)/);
        if (!match) return;
        var target = parseFloat(match[1]);
        if (isNaN(target) || target === 0) return;
        var suffix = text.slice(match[1].length);
        var decimals = match[1].includes('.') ? match[1].split('.')[1].length : 0;
        var duration = 600;
        var start = performance.now();
        function step(now) {
            var t = Math.min((now - start) / duration, 1);
            t = 1 - Math.pow(1 - t, 3);
            var val = (target * t).toFixed(decimals);
            el.textContent = val + suffix;
            if (t < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }
    setTimeout(function() {
        document.querySelectorAll('.pf-ms-value, .pf-metric-value').forEach(countUp);
    }, 100);
})();
</script>
"""
st.markdown(_COUNTUP_JS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# PLOTLY — shared chart template (design-system aligned)
# ═══════════════════════════════════════════════════════════════════════

_PF_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Figtree, sans-serif", color="#E8ECF4", size=11),
    margin=dict(l=40, r=20, t=30, b=30),
    height=250,
    xaxis=dict(gridcolor="rgba(148,163,194,0.06)", zeroline=False),
    yaxis=dict(gridcolor="rgba(148,163,194,0.08)", zeroline=False),
    legend=dict(font=dict(color="#8B95AD", size=10)),
    hoverlabel=dict(
        bgcolor="#1A1D2B",
        bordercolor="rgba(148,163,194,0.12)",
        font=dict(color="#E8ECF4", family="Figtree, sans-serif"),
    ),
)


def _pf_layout(**overrides):
    """Return chart layout dict with design-system defaults, accepting overrides."""
    merged = dict(_PF_CHART_LAYOUT)
    merged.update(overrides)
    return merged


# ═══════════════════════════════════════════════════════════════════════
# HELPER: HTML rendering functions
# ═══════════════════════════════════════════════════════════════════════

def _render_brand(size: str = "normal") -> str:
    """Return brand HTML with logo + wordmark."""
    if size == "large":
        img = f'<img src="{_LOGO_URI}" alt="PaceForge">' if _LOGO_URI else ""
        return f"""
        <div class="pf-auth-hero">
            {img}
            <h1 class="pf-auth-title">PACE<span>FORGE</span></h1>
            <p class="pf-auth-subtitle">AI-Powered Running Coach</p>
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


def _metrics_strip(items: list[tuple[str, str, str]]) -> str:
    """Render a horizontal metrics strip with divide-x separators.

    items: list of (label, value, unit) tuples.
    """
    cells = []
    for label, value, unit in items:
        unit_html = f'<span class="pf-ms-unit">{unit}</span>' if unit else ""
        cells.append(
            f'<div class="pf-ms-item">'
            f'<div class="pf-ms-label">{label}</div>'
            f'<div class="pf-ms-value">{value}{unit_html}</div>'
            f'</div>'
        )
    return f'<div class="pf-metrics-strip">{"".join(cells)}</div>'


def _splits_table_html(laps: list[dict], show_pace_bars: bool = True) -> str:
    """Render a splits table with optional pace bars."""
    if not laps:
        return ""

    rows = []
    paces = []
    for i, lap in enumerate(laps, 1):
        lap_dist = lap.get("distance", 0)
        lap_speed = lap.get("averageSpeed", 0)
        lap_pace = (1000 / lap_speed) if lap_speed else 0
        lap_hr = lap.get("averageHR", 0)
        paces.append(lap_pace)
        rows.append((i, lap_dist, lap_pace, lap_hr))

    # Calculate pace bar widths relative to slowest pace
    max_pace = max(paces) if paces else 1
    avg_pace = sum(paces) / len(paces) if paces else 0

    body = ""
    for i, dist, pace, hr in rows:
        bar_pct = (pace / max_pace * 100) if max_pace and show_pace_bars else 0
        bar_color = "#10B981" if pace <= avg_pace else "#F43F5E"
        pace_bar = f'<div class="pf-pace-bar" style="width:{bar_pct:.0f}%;background:{bar_color};"></div>' if show_pace_bars else ""
        body += (
            f'<tr>'
            f'<td>{i}</td>'
            f'<td>{_fmt_dist(dist)}</td>'
            f'<td class="pf-pace-cell" style="position:relative;">{_fmt_pace(pace)}{pace_bar}</td>'
            f'<td>{int(hr) if hr else chr(8212)}</td>'
            f'</tr>'
        )

    return (
        f'<table class="pf-splits-table">'
        f'<thead><tr><th>Split</th><th>Dist</th><th>Pace</th><th>HR</th></tr></thead>'
        f'<tbody>{body}</tbody></table>'
    )


def _hr_zone_bars_html(hr_list: list[dict]) -> str:
    """Render CSS-only horizontal HR zone bars."""
    if not hr_list:
        return ""

    zone_colors = ["#3F51B5", "#0EA5E9", "#34D399", "#F59E0B", "#F43F5E"]
    total_secs = sum(zd.get("secsInZone", 0) for zd in hr_list) or 1

    bars = []
    for zd in hr_list:
        zn = zd.get("zoneNumber") or zd.get("zone", 0)
        secs = zd.get("secsInZone", 0)
        color = zone_colors[zn - 1] if 1 <= zn <= 5 else "#607D8B"
        pct = (secs / total_secs) * 100
        time_str = _fmt_duration(secs)

        bars.append(
            f'<div class="pf-hz-bar-row">'
            f'<div class="pf-hz-label" style="color:{color};">Z{zn}</div>'
            f'<div class="pf-hz-track">'
            f'<div class="pf-hz-fill" style="width:{pct:.1f}%;background:{color};">'
            f'{f"<span class=pf-hz-time>{time_str}</span>" if pct > 12 else ""}'
            f'</div></div>'
            f'<div style="font-family:var(--font-mono);font-size:0.65rem;color:#8B95AD;width:44px;text-align:right;">'
            f'{time_str if pct <= 12 else ""}</div>'
            f'</div>'
        )

    return (
        f'<div style="font-family:Manrope,sans-serif;font-weight:600;font-size:0.82rem;'
        f'color:#8B95AD;margin-bottom:6px;">HR Zones</div>'
        f'<div style="display:flex;flex-direction:column;gap:2px;">{"".join(bars)}</div>'
    )


def _skeleton_cards(count: int = 3) -> str:
    """Render skeleton loading placeholder cards."""
    cards = []
    for _ in range(count):
        cards.append(
            '<div class="pf-skeleton-card">'
            '<div class="pf-skeleton pf-skeleton-text" style="width:50%;margin:0 auto 8px;"></div>'
            '<div class="pf-skeleton pf-skeleton-value"></div>'
            '</div>'
        )
    return (
        f'<div style="display:grid;grid-template-columns:repeat({count},1fr);gap:12px;">'
        f'{"".join(cards)}</div>'
    )


_WORKOUT_COLORS = {
    "easy_run": "#34D399",
    "recovery_run": "#6EE7B7",
    "easy_with_strides": "#4ADE80",
    "long_run": "#0EA5E9",
    "long_run_progressive": "#0284C7",
    "long_run_with_race_pace": "#0369A1",
    "tempo": "#F59E0B",
    "threshold": "#D97706",
    "intervals": "#F43F5E",
    "vo2max": "#E11D48",
    "speed": "#E11D48",
    "hills": "#BE123C",
    "fartlek": "#FB923C",
    "progressive": "#FBBF24",
    "race_pace": "#D97706",
    "rest": "#6B7280",
}

_PACE_COLORS = {
    "Easy": "#34D399",
    "Marathon": "#0EA5E9",
    "Threshold": "#F59E0B",
    "Interval": "#F43F5E",
}

_PHASE_COLORS = {
    "base": "rgba(16,185,129,0.12)",
    "build": "rgba(14,165,233,0.12)",
    "peak": "rgba(245,158,11,0.12)",
    "taper": "rgba(139,92,246,0.12)",
    "race": "rgba(244,63,94,0.12)",
}

_PHASE_TEXT = {
    "base": "#10B981",
    "build": "#0EA5E9",
    "peak": "#F59E0B",
    "taper": "#8B5CF6",
    "race": "#F43F5E",
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
    # CookieManager needs one Streamlit cycle to initialize its JS iframe.
    # On the very first run after a page refresh, get() returns None even
    # when cookies exist.  Rerun once to let the component load.
    if not st.session_state.get("_cookie_init"):
        st.session_state["_cookie_init"] = True
        time.sleep(0.5)
        st.rerun()
    saved_jwt = _cookie_mgr.get("pf_jwt")
    saved_refresh = _cookie_mgr.get("pf_refresh")
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
            elif saved_refresh:
                # Access token expired — try refreshing
                rr = requests.post(
                    f"{API_BASE}/auth/refresh",
                    json={"refresh_token": saved_refresh},
                    timeout=10,
                )
                if rr.status_code == 200:
                    data = rr.json()
                    st.session_state.jwt = data["access_token"]
                    st.session_state.role = data["role"]
                    st.session_state.user_name = data["name"]
                    st.session_state.user_email = data.get("email", "")
                    st.session_state.page = "app"
                    _cookie_mgr.set("pf_jwt", data["access_token"], key="set_jwt_refresh1", max_age=86400)
                    _cookie_mgr.set("pf_refresh", data["refresh_token"], key="set_refresh_refresh1", max_age=2592000)
        except Exception:
            pass  # Cookie invalid or API unreachable — show login
    elif saved_refresh:
        # No access token cookie but refresh token exists — try refreshing
        try:
            rr = requests.post(
                f"{API_BASE}/auth/refresh",
                json={"refresh_token": saved_refresh},
                timeout=10,
            )
            if rr.status_code == 200:
                data = rr.json()
                st.session_state.jwt = data["access_token"]
                st.session_state.role = data["role"]
                st.session_state.user_name = data["name"]
                st.session_state.user_email = data.get("email", "")
                st.session_state.page = "app"
                _cookie_mgr.set("pf_jwt", data["access_token"], key="set_jwt_refresh2", max_age=86400)
                _cookie_mgr.set("pf_refresh", data["refresh_token"], key="set_refresh_refresh2", max_age=2592000)
        except Exception:
            pass


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
    _cookie_mgr.delete("pf_refresh")


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
        return f"<span class='pf-dot pf-dot-emerald'></span><b>{dist_str}</b> warm up at a conversational pace{pace_hint}"
    elif stype == "cooldown":
        return f"<span class='pf-dot pf-dot-sky'></span><b>{dist_str}</b> cool down at a conversational pace (or slower!)"
    elif stype == "recovery":
        return f"<span class='pf-dot pf-dot-muted'></span><b>{dist_str}</b> recovery jog"
    elif stype == "rest":
        return f"<span class='pf-dot pf-dot-muted'></span><b>{dist_str}</b> walking rest"
    else:  # active / interval leaf
        if target_type == "pace" and target_low:
            return f"<span class='pf-dot pf-dot-rose'></span><b>{dist_str}</b> at {_fmt_pace(target_low)}"
        elif target_type == "open" or not target_low:
            return f"<span class='pf-dot pf-dot-emerald'></span><b>{dist_str}</b> at an easy, conversational pace"
        else:
            return f"<span class='pf-dot pf-dot-amber'></span><b>{dist_str}</b> at {_fmt_pace(target_low)}"


def _render_workout_detail(workout: dict, plan_paces: dict | None = None) -> str:
    """Render a structured workout description as HTML."""
    steps = workout.get("steps", [])
    name = workout.get("name", "Workout")
    purpose = workout.get("purpose", "")
    est_dist = _fmt_dist(workout.get("estimated_distance_meters"))
    est_dur = _fmt_duration(workout.get("estimated_duration_seconds"))
    notes = workout.get("notes", "")

    lines = []
    lines.append(f'<div style="font-weight:700;font-size:1.1rem;margin-bottom:0.5rem;">{name}</div>')
    if purpose:
        lines.append(f'<div style="color:#8B95AD;margin-bottom:0.75rem;font-size:0.85rem;">{purpose}</div>')

    # Summary badges
    badges = []
    if est_dist and est_dist != "—":
        badges.append(f'<span style="background:#1A1D2B;padding:4px 10px;border-radius:12px;font-size:0.8rem;margin-right:6px;">{est_dist}</span>')
    if est_dur and est_dur != "—":
        badges.append(f'<span style="background:#1A1D2B;padding:4px 10px;border-radius:12px;font-size:0.8rem;margin-right:6px;">{est_dur}</span>')
    if badges:
        lines.append(f'<div style="margin-bottom:0.75rem;">{"".join(badges)}</div>')

    if not steps:
        lines.append('<div style="color:#8B95AD;">No structured steps available.</div>')
    else:
        lines.append('<div style="font-weight:600;font-size:0.9rem;margin-bottom:0.5rem;color:#10B981;">Workout Structure</div>')
        for step in steps:
            rc = step.get("repeat_count")
            nested = step.get("steps", [])
            if rc and nested:
                lines.append(
                    f'<div style="margin:0.5rem 0;padding:0.5rem 0.75rem;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.15);border-radius:8px;">'
                    f'<div style="font-weight:600;color:#F59E0B;margin-bottom:0.25rem;">Repeat {rc}×</div>'
                )
                for sub in nested:
                    lines.append(f'<div style="padding:2px 0;">{_render_step_line(sub)}</div>')
                lines.append("</div>")
            else:
                lines.append(f'<div style="padding:3px 0;">{_render_step_line(step)}</div>')

    if notes:
        lines.append(f'<div style="margin-top:0.75rem;color:#8B95AD;font-size:0.8rem;font-style:italic;">{notes}</div>')

    return f'<div class="pf-card" style="margin-top:1rem;">{"".join(lines)}</div>'


def _render_garmin_activity_detail(detail: dict, activity_type: str = "running") -> None:
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

    _is_run = activity_type in ("running", "trail_running", "treadmill_running")
    if _is_run:
        metric_data = [
            ("Distance", _fmt_dist(total_dist), ""),
            ("Duration", _fmt_duration(total_dur / 1000 if total_dur > 10000 else total_dur), ""),
            ("Avg Pace", _fmt_pace(avg_pace) if avg_pace else "—", ""),
        ]
    else:
        metric_data = [
            ("Duration", _fmt_duration(total_dur / 1000 if total_dur > 10000 else total_dur), ""),
        ]
        if total_dist and total_dist > 100:
            metric_data.append(("Distance", _fmt_dist(total_dist), ""))
    if avg_hr:
        metric_data.append(("Avg HR", f"{int(avg_hr)}", "bpm"))
    if max_hr:
        metric_data.append(("Max HR", f"{int(max_hr)}", "bpm"))
    if cadence:
        metric_data.append(("Cadence", f"{int(cadence * 2)}", "spm"))
    if calories:
        metric_data.append(("Calories", f"{int(calories)}", ""))
    if elevation:
        metric_data.append(("Elevation", f"{int(elevation)}", "m"))
    if aero_te:
        metric_data.append(("Aerobic TE", f"{aero_te:.1f}", ""))
    if anaero_te:
        metric_data.append(("Anaerobic TE", f"{anaero_te:.1f}", ""))

    st.markdown(_metrics_strip(metric_data), unsafe_allow_html=True)

    # ── Weather info ──
    if weather_data and isinstance(weather_data, dict):
        temp = weather_data.get("temp")
        cond = weather_data.get("weatherTypeDTO", {}).get("desc") if isinstance(weather_data.get("weatherTypeDTO"), dict) else None
        humidity = weather_data.get("relativeHumidity")
        wind = weather_data.get("windSpeed")
        parts = []
        if temp is not None:
            parts.append(f"{temp}°C")
        if cond:
            parts.append(cond)
        if humidity is not None:
            parts.append(f"{humidity}%")
        if wind is not None:
            parts.append(f"{wind} km/h")
        if parts:
            st.markdown(
                f'<div style="color:#8B95AD;font-size:0.75rem;margin-bottom:0.5rem;">{" · ".join(parts)}</div>',
                unsafe_allow_html=True,
            )

    # ── Splits ──
    laps = (splits_data.get("lapDTOs") or []) if _is_run else []
    if laps:
        st.markdown(
            f'<div class="pf-card" style="margin-bottom:0.5rem;padding:0.75rem;">'
            f'{_splits_table_html(laps)}</div>',
            unsafe_allow_html=True,
        )

        # Collect data for chart
        split_nums = list(range(1, len(laps) + 1))
        paces = []
        hrs = []
        for lap in laps:
            lap_speed = lap.get("averageSpeed", 0)
            paces.append((1000 / lap_speed) if lap_speed else 0)
            hrs.append(lap.get("averageHR", 0))

        # Combined pace + HR chart over splits
        if paces and any(h > 0 for h in hrs):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            avg_p = sum(paces) / len(paces)
            colors = ["#10B981" if p <= avg_p else "#F43F5E" for p in paces]

            fig.add_trace(
                go.Bar(
                    x=split_nums, y=paces, name="Pace",
                    marker_color=colors,
                    text=[_fmt_pace(p) for p in paces],
                    textposition="outside",
                    textfont=dict(color="#E8ECF4", size=9),
                ),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(
                    x=split_nums, y=hrs, name="Heart Rate",
                    mode="lines+markers",
                    line=dict(color="#F43F5E", width=2),
                    marker=dict(size=5),
                ),
                secondary_y=True,
            )
            fig.update_layout(**_pf_layout(
                margin=dict(l=40, r=40, t=25, b=35), height=240,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10, color="#8B95AD")),
                bargap=0.3,
            ))
            fig.update_yaxes(autorange="reversed", title_text="Pace (s/km)", gridcolor="rgba(148,163,194,0.08)", secondary_y=False)
            fig.update_yaxes(title_text="HR (bpm)", gridcolor="rgba(148,163,194,0.08)", secondary_y=True)
            fig.update_xaxes(title_text="Split", gridcolor="rgba(148,163,194,0.06)", dtick=1)
            st.plotly_chart(fig, use_container_width=True, key="splits_hr_chart")
        elif paces:
            avg_p = sum(paces) / len(paces)
            colors = ["#10B981" if p <= avg_p else "#F43F5E" for p in paces]
            fig = go.Figure(go.Bar(
                x=split_nums, y=paces, marker_color=colors,
                text=[_fmt_pace(p) for p in paces], textposition="outside",
                textfont=dict(color="#E8ECF4", size=9),
            ))
            fig.update_layout(**_pf_layout(
                margin=dict(l=40, r=20, t=25, b=35), height=220,
                yaxis=dict(autorange="reversed", title="Pace (s/km)", gridcolor="rgba(148,163,194,0.08)", zeroline=False),
                xaxis=dict(gridcolor="rgba(148,163,194,0.06)", dtick=1, title="Split", zeroline=False),
                bargap=0.3,
            ))
            st.plotly_chart(fig, use_container_width=True, key="splits_chart")

    # ── HR Zones ──
    hr_list = hr_zones_data if isinstance(hr_zones_data, list) else hr_zones_data.get("hrTimeInZones", [])
    if hr_list and any(zd.get("secsInZone", 0) > 0 for zd in hr_list):
        st.markdown(
            f'<div class="pf-card" style="padding:0.75rem;">{_hr_zone_bars_html(hr_list)}</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════
# AUTH GATE
# ═══════════════════════════════════════════════════════════════════════

if st.session_state.jwt is None:
    # Centered auth container
    _left, auth_col, _right = st.columns([1, 1.2, 1])

    with auth_col:
        st.markdown('<div class="pf-auth-container">', unsafe_allow_html=True)
        st.markdown(_render_brand("large"), unsafe_allow_html=True)

        if st.session_state.page == "register":
            st.markdown('<div class="pf-auth-form">', unsafe_allow_html=True)
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
            st.markdown('<div class="pf-auth-form">', unsafe_allow_html=True)
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
                        _cookie_mgr.set("pf_jwt", data["access_token"], key="set_jwt_login", max_age=86400)
                        _cookie_mgr.set("pf_refresh", data["refresh_token"], key="set_refresh_login", max_age=2592000)
                        st.rerun()
                    elif r.status_code == 403:
                        st.warning(_error_detail(r))
                    else:
                        st.error(_error_detail(r))
                except requests.ConnectionError:
                    st.error("Cannot reach PaceForge API. Is the server running?")

            st.markdown("")
            st.markdown(
                '<p class="pf-auth-footer">Don\'t have an account?</p>',
                unsafe_allow_html=True,
            )
            if st.button("Create Account", use_container_width=True):
                st.session_state.page = "register"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)  # close pf-auth-container

    st.stop()


# ═══════════════════════════════════════════════════════════════════════
# MAIN APP — authenticated
# ═══════════════════════════════════════════════════════════════════════

# ── Auto-restore Garmin connection, plan, and activities on load ─────
if not st.session_state._restored and st.session_state.jwt:
    with st.spinner("Loading your training data..."):
        _restore_ok = False

        # 1) Check Garmin connection (triggers auto-reconnect from cached tokens)
        try:
            r = requests.get(
                f"{API_BASE}/garmin/status",
                headers=_auth_headers(),
                timeout=10,
            )
            if r.status_code == 200:
                status_data = r.json()
                if status_data.get("connected"):
                    st.session_state.garmin_logged_in = True
                st.session_state["last_synced"] = status_data.get("last_synced")
                _restore_ok = True
        except Exception:
            logging.warning("Failed to check Garmin status on restore", exc_info=True)

        # 2) Restore plans from DB cache
        try:
            if not st.session_state.plans:
                r = requests.get(
                    f"{API_BASE}/plans",
                    headers=_auth_headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    st.session_state.plans = r.json()
        except Exception:
            logging.warning("Failed to restore plans on startup", exc_info=True)

        # 3) Restore activities from DB cache
        try:
            if not st.session_state.get("garmin_activities"):
                r = requests.get(
                    f"{API_BASE}/activities?days=240",
                    headers=_auth_headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    st.session_state["garmin_activities"] = r.json()
        except Exception:
            logging.warning("Failed to restore activities on startup", exc_info=True)

        # 4) Restore fitness profile from DB cache
        try:
            if not st.session_state.get("profile"):
                r = requests.get(
                    f"{API_BASE}/profile",
                    headers=_auth_headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    st.session_state.profile = r.json()
        except Exception:
            logging.warning("Failed to restore profile on startup", exc_info=True)

        # 5) Pre-load analytics from cached profile
        try:
            if not st.session_state.get("analytics") and st.session_state.get("profile"):
                r = requests.get(
                    f"{API_BASE}/profile/analytics",
                    headers=_auth_headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    st.session_state.analytics = r.json()
        except Exception:
            logging.warning("Failed to restore analytics on startup", exc_info=True)

        # 6) Fetch scheduled workouts from Garmin calendar
        try:
            if st.session_state.garmin_logged_in and not st.session_state.get("garmin_scheduled"):
                r = requests.get(
                    f"{API_BASE}/garmin/scheduled-workouts",
                    headers=_auth_headers(),
                    timeout=15,
                )
                if r.status_code == 200:
                    st.session_state["garmin_scheduled"] = r.json()
        except Exception:
            logging.warning("Failed to fetch scheduled workouts on startup", exc_info=True)

    # Only mark restored if at least the first API call succeeded — prevents
    # locking out retries when JWT isn't ready or API is temporarily down.
    if _restore_ok:
        st.session_state._restored = True
        st.rerun()  # Rerun so calendar renders with freshly loaded data

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
            '<div style="background:#10B98122;color:#10B981;padding:6px 12px;border-radius:8px;'
            'font-size:0.8rem;font-weight:600;text-align:center;margin-bottom:0.5rem;">'
            '⌚ Garmin Connected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#F59E0B22;color:#F59E0B;padding:6px 12px;border-radius:8px;'
            'font-size:0.8rem;font-weight:600;text-align:center;margin-bottom:0.5rem;">'
            '⌚ Garmin Not Connected</div>',
            unsafe_allow_html=True,
        )

    if st.button("Logout", use_container_width=True):
        _logout()
        st.rerun()


# ── Garmin Sync Status Banner ──────────────────────────────────────

_last_synced = st.session_state.get("last_synced")
_sync_text = ""
if _last_synced:
    try:
        from datetime import datetime as _dt
        _ts = _dt.fromisoformat(_last_synced.replace("Z", "+00:00"))
        _sync_text = f"Last synced: {_ts.strftime('%b %d, %Y %H:%M UTC')}"
    except Exception:
        _sync_text = f"Last synced: {_last_synced[:19]}"

if not st.session_state.garmin_logged_in:
    st.markdown(
        f'<div style="background:#2D2000;border:1px solid #F59E0B;border-radius:8px;'
        f'padding:0.5rem 1rem;margin-bottom:1rem;color:#FFB74D;font-size:0.85rem;">'
        f'Garmin not connected — showing cached data'
        f'{" · " + _sync_text if _sync_text else ""}. '
        f'Connect via the sidebar to refresh.</div>',
        unsafe_allow_html=True,
    )
else:
    _banner_cols = st.columns([5, 1])
    with _banner_cols[0]:
        st.markdown(
            f'<div style="background:#0D2818;border:1px solid #10B981;border-radius:8px;'
            f'padding:0.5rem 1rem;color:#69F0AE;font-size:0.85rem;">'
            f'Garmin connected{" · " + _sync_text if _sync_text else ""}</div>',
            unsafe_allow_html=True,
        )
    with _banner_cols[1]:
        if st.button("Sync Garmin", key="sync_garmin_all", use_container_width=True):
            with st.spinner("Syncing from Garmin Connect..."):
                _sync_ok = []
                _sync_err = []
                try:
                    r = requests.get(f"{API_BASE}/profile?sync=true", headers=_auth_headers(), timeout=60)
                    if r.status_code == 200:
                        st.session_state.profile = r.json()
                        st.session_state.pop("analytics", None)
                        _sync_ok.append("profile")
                    else:
                        _sync_err.append(f"profile ({r.status_code}: {r.text[:100]})")
                except Exception as _e:
                    _sync_err.append(f"profile ({_e})")
                try:
                    r = requests.get(
                        f"{API_BASE}/activities?days=240&sync=true",
                        headers=_auth_headers(), timeout=60,
                    )
                    if r.status_code == 200:
                        st.session_state["garmin_activities"] = r.json()
                        st.session_state.pop("cal_selected_event", None)
                        st.session_state.pop("cal_selected_detail", None)
                        _sync_ok.append(f"{len(r.json())} activities")
                    else:
                        _sync_err.append(f"activities ({r.status_code}: {r.text[:100]})")
                except Exception as _e:
                    _sync_err.append(f"activities ({_e})")
                # Refresh plans (picks up auto-matched completions)
                try:
                    r = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
                    if r.status_code == 200:
                        st.session_state.plans = r.json()
                except Exception:
                    pass
                # Refresh scheduled workouts from Garmin calendar
                try:
                    r = requests.get(f"{API_BASE}/garmin/scheduled-workouts", headers=_auth_headers(), timeout=15)
                    if r.status_code == 200:
                        st.session_state["garmin_scheduled"] = r.json()
                except Exception:
                    pass
                if _sync_ok:
                    st.success(f"Synced: {', '.join(_sync_ok)}")
                if _sync_err:
                    st.error(f"Failed to sync: {', '.join(_sync_err)}")
                if _sync_ok and not _sync_err:
                    st.rerun()


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
        _header_stats.append(("VO\u2082", str(_p["vo2_max"]), "#10B981"))
    if _p.get("resting_hr"):
        _header_stats.append(("RHR", f"{_p['resting_hr']} bpm", "#4DA6FF"))
    if _p.get("weekly_mileage_km"):
        _header_stats.append(("Weekly", f"{_p['weekly_mileage_km']} km", "#8B5CF6"))
    if _p.get("body_battery_current"):
        _bb = _p["body_battery_current"]
        _bb_color = "#10B981" if _bb >= 50 else "#F59E0B" if _bb >= 25 else "#FF5252"
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
            f'<div style="background:#10B98115;border:1px solid #10B98133;border-radius:10px;'
            f'padding:6px 14px;display:flex;align-items:center;gap:6px;">'
            f'<span style="font-size:0.85rem;">\u2705</span>'
            f'<span style="color:#10B981;font-weight:600;font-size:0.85rem;">{_wo_name}</span>'
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
        '<div style="background:#10B98115;border:1px solid #10B98133;border-radius:10px;'
        'padding:6px 14px;display:flex;align-items:center;gap:6px;">'
        '<span style="font-size:0.85rem;">\U0001f634</span>'
        '<span style="color:#69F0AE;font-weight:600;font-size:0.85rem;">Rest day</span>'
        '</div>'
    )

# Greeting based on time of day
_hour = _dt_now.now().hour
_greeting = "Good morning" if _hour < 12 else "Good afternoon" if _hour < 18 else "Good evening"

st.markdown(
    f'<div style="background:linear-gradient(135deg, #161821 0%, #252830 100%);'
    f'border:1px solid #252A35;border-radius:14px;padding:1rem 1.5rem;margin-bottom:1rem;'
    f'display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap;">'
    # Avatar
    f'<div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#10B981,#00A854);'
    f'display:flex;align-items:center;justify-content:center;color:#fff;'
    f'font-weight:700;font-size:1rem;flex-shrink:0;">{_header_initials}</div>'
    # Greeting + name
    f'<div style="flex:1;min-width:140px;">'
    f'<div style="color:#8B95AD;font-size:0.8rem;">{_greeting}</div>'
    f'<div style="color:#E8ECF4;font-weight:600;font-size:1.15rem;">{_user_display_name}</div>'
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

tab_names = ["Feed", "Fitness Profile", "Training Plan", "Calendar", "HYROX", "AI Coach", "User Profile"]
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
    # ── Friend Profile View ──
    _viewing_uid = st.session_state.get("viewing_profile_id")
    if _viewing_uid:
        if st.button("← Back to Feed", key="back_to_feed"):
            st.session_state.pop("viewing_profile_id", None)
            st.session_state.pop("_profile_cache", None)
            st.rerun()

        # Fetch profile data
        if "_profile_cache" not in st.session_state or st.session_state.get("_profile_cache_uid") != _viewing_uid:
            try:
                _pf_r = requests.get(
                    f"{API_BASE}/users/{_viewing_uid}/profile",
                    headers=_auth_headers(), timeout=15,
                )
                st.session_state._profile_cache = _pf_r.json() if _pf_r.status_code == 200 else None
                st.session_state._profile_cache_uid = _viewing_uid
                if _pf_r.status_code == 403:
                    st.session_state._profile_cache = {"error": "not_friend"}
            except Exception:
                st.session_state._profile_cache = None

        _pdata = st.session_state.get("_profile_cache")
        if _pdata and _pdata.get("error") == "not_friend":
            st.warning("You can only view profiles of friends.")
        elif _pdata:
            _p_name = _pdata.get("name", "Unknown")
            _p_initials = "".join(w[0].upper() for w in _p_name.split()[:2]) if _p_name else "?"

            # Header
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:1rem;margin-bottom:1.5rem;">'
                f'<div style="width:56px;height:56px;border-radius:50%;background:#10B98133;'
                f'display:flex;align-items:center;justify-content:center;color:#10B981;'
                f'font-weight:700;font-size:1.3rem;">{_p_initials}</div>'
                f'<div><div style="color:#E8ECF4;font-weight:700;font-size:1.3rem;">{_p_name}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # ── Fitness Highlights ──
            _p_profile = _pdata.get("profile")
            if _p_profile:
                st.markdown('<div class="pf-section-header" style="font-size:0.95rem;">Fitness Profile</div>', unsafe_allow_html=True)
                _fp_items = []
                if _p_profile.get("vo2_max"):
                    _fp_items.append(("VO2 Max", f"{_p_profile['vo2_max']:.1f}", ""))
                if _p_profile.get("resting_hr"):
                    _fp_items.append(("Resting HR", str(_p_profile["resting_hr"]), "bpm"))
                if _p_profile.get("max_hr"):
                    _fp_items.append(("Max HR", str(_p_profile["max_hr"]), "bpm"))
                if _p_profile.get("training_status"):
                    _fp_items.append(("Status", _p_profile["training_status"], ""))
                if _p_profile.get("training_readiness"):
                    _fp_items.append(("Readiness", f"{_p_profile['training_readiness']:.0f}", ""))
                if _p_profile.get("hrv_status"):
                    _fp_items.append(("HRV", _p_profile["hrv_status"], ""))
                if _p_profile.get("weekly_mileage_km"):
                    _fp_items.append(("Weekly", f"{_p_profile['weekly_mileage_km']:.1f}", "km"))
                if _fp_items:
                    st.markdown(_metrics_strip(_fp_items), unsafe_allow_html=True)

            # ── Training Plan ──
            _p_plan = _pdata.get("plan")
            if _p_plan:
                st.markdown('<div class="pf-section-header" style="font-size:0.95rem;margin-top:1rem;">Training Plan</div>', unsafe_allow_html=True)
                _plan_pct = _p_plan.get("progress_pct", 0)
                _plan_bar_color = "#10B981" if _plan_pct >= 50 else "#F59E0B"
                st.markdown(
                    f'<div class="pf-card">'
                    f'<div style="color:#E8ECF4;font-weight:600;margin-bottom:0.3rem;">{_p_plan.get("name", "Plan")}</div>'
                    f'<div style="color:#8B95AD;font-size:0.85rem;margin-bottom:0.5rem;">'
                    f'Goal: {_p_plan.get("goal_type", "")} · Target: {_p_plan.get("target_date", "")}'
                    f'</div>'
                    f'<div style="background:#252A35;border-radius:4px;height:8px;overflow:hidden;margin-bottom:0.3rem;">'
                    f'<div style="background:{_plan_bar_color};height:100%;width:{_plan_pct}%;border-radius:4px;"></div>'
                    f'</div>'
                    f'<div style="color:#8B95AD;font-size:0.8rem;">'
                    f'{_p_plan.get("completed_workouts", 0)}/{_p_plan.get("total_workouts", 0)} workouts completed ({_plan_pct}%)'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # ── Recent Activities ──
            _p_acts = _pdata.get("activities", [])
            if _p_acts:
                st.markdown('<div class="pf-section-header" style="font-size:0.95rem;margin-top:1rem;">Recent Activities</div>', unsafe_allow_html=True)
                _act_rows_html = ""
                for _pa in _p_acts[:15]:
                    _pa_name = _pa.get("name", "Activity")
                    _pa_type = _pa.get("activity_type", "running")
                    _pa_date = str(_pa.get("start_time", ""))[:10]
                    _pa_dist = _pa.get("distance_meters", 0)
                    _pa_dur = _pa.get("duration_seconds", 0)
                    _pa_pace = _pa.get("avg_pace_sec_per_km")
                    _pa_hr = _pa.get("avg_hr")
                    _pa_is_run = _pa_type in ("running", "trail_running", "treadmill_running")

                    _pa_parts = []
                    if _pa_is_run and _pa_dist:
                        _pa_parts.append(f"{_pa_dist / 1000:.1f}km")
                    if _pa_dur:
                        _pdm, _pds = divmod(int(_pa_dur), 60)
                        _pa_parts.append(f"{_pdm}:{_pds:02d}")
                    if _pa_is_run and _pa_pace:
                        _ppm, _pps = divmod(int(_pa_pace), 60)
                        _pa_parts.append(f"{_ppm}:{_pps:02d}/km")
                    if _pa_hr:
                        _pa_parts.append(f"{_pa_hr}bpm")
                    _pa_detail = " · ".join(_pa_parts)

                    _pa_type_color = "#10B981" if _pa_is_run else "#A78BFA"
                    _act_rows_html += (
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:0.45rem 0;border-bottom:1px solid #252A35;">'
                        f'<div>'
                        f'<span style="color:#8B95AD;font-size:0.75rem;margin-right:0.5rem;">{_pa_date}</span>'
                        f'<span style="color:{_pa_type_color};font-size:0.65rem;margin-right:0.4rem;">●</span>'
                        f'<span style="color:#E8ECF4;font-weight:500;font-size:0.9rem;">{_pa_name}</span>'
                        f'</div>'
                        f'<div style="color:#8B95AD;font-size:0.82rem;white-space:nowrap;">{_pa_detail}</div>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div class="pf-card" style="padding:0.8rem;">{_act_rows_html}</div>',
                    unsafe_allow_html=True,
                )

            # ── HYROX Races ──
            _p_hyrox = _pdata.get("hyrox")
            if _p_hyrox:
                _hyrox_results = _p_hyrox.get("results", []) if isinstance(_p_hyrox, dict) else _p_hyrox if isinstance(_p_hyrox, list) else []
                if _hyrox_results:
                    st.markdown('<div class="pf-section-header" style="font-size:0.95rem;margin-top:1rem;">HYROX Races</div>', unsafe_allow_html=True)
                    for _hr in _hyrox_results:
                        _hr_time = _hr.get("total_time_display", "")
                        _hr_city = _hr.get("city", "")
                        _hr_date = _hr.get("event_date", "")
                        _hr_div = _hr.get("division", "")
                        _hr_rank = _hr.get("rank", "")
                        _hr_rank_g = _hr.get("rank_gender", "")
                        _hr_parts = []
                        if _hr_rank:
                            _hr_parts.append(f"Overall: #{_hr_rank}")
                        if _hr_rank_g:
                            _hr_parts.append(f"Gender: #{_hr_rank_g}")
                        _hr_rank_str = " · ".join(_hr_parts)
                        st.markdown(
                            f'<div class="pf-card" style="margin-bottom:0.5rem;">'
                            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                            f'<div>'
                            f'<span style="color:#E8ECF4;font-weight:600;">{_hr_city}</span>'
                            f'<span style="color:#8B95AD;font-size:0.8rem;margin-left:0.5rem;">{_hr_date}</span>'
                            f'</div>'
                            f'<div style="color:#10B981;font-weight:700;font-size:1.1rem;">{_hr_time}</div>'
                            f'</div>'
                            + (f'<div style="color:#8B95AD;font-size:0.8rem;margin-top:0.2rem;">{_hr_div}</div>' if _hr_div else '')
                            + (f'<div style="color:#8B95AD;font-size:0.78rem;margin-top:0.15rem;">{_hr_rank_str}</div>' if _hr_rank_str else '')
                            + f'</div>',
                            unsafe_allow_html=True,
                        )

            # ── Recent Feed Activity ──
            _p_feed = _pdata.get("feed", [])
            if _p_feed:
                st.markdown('<div class="pf-section-header" style="font-size:0.95rem;margin-top:1rem;">Recent Activity</div>', unsafe_allow_html=True)
                for _pf_ev in _p_feed[:10]:
                    _pf_date = _pf_ev.get("created_at", "")[:10]
                    st.markdown(
                        f'<div style="padding:0.35rem 0;border-bottom:1px solid #252A3522;">'
                        f'<span style="color:#8B95AD;font-size:0.75rem;margin-right:0.5rem;">{_pf_date}</span>'
                        f'<span style="color:#E8ECF4;font-size:0.9rem;">{_pf_ev.get("title", "")}</span>'
                        + (f'<span style="color:#8B95AD;font-size:0.8rem;margin-left:0.5rem;">{_pf_ev.get("body", "")}</span>'
                           if _pf_ev.get("body") else '')
                        + f'</div>',
                        unsafe_allow_html=True,
                    )

            if not _p_profile and not _p_acts and not _p_plan and not (_p_hyrox and _hyrox_results):
                st.markdown(
                    '<div style="text-align:center;padding:2rem;color:#8B95AD;">'
                    "This user hasn't synced any data yet.</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.error("Could not load profile data.")

    else:
        # ── Normal Feed View ──
        st.markdown('<div class="pf-section-header">Activity Feed</div>', unsafe_allow_html=True)

        if "feed_events" not in st.session_state:
            try:
                feed_r = requests.get(
                    f"{API_BASE}/feed?limit=30&offset=0",
                    headers=_auth_headers(), timeout=10,
                )
                st.session_state.feed_events = feed_r.json() if feed_r.status_code == 200 else []
            except Exception:
                st.session_state.feed_events = []
        feed_events = st.session_state.feed_events

        if st.button("Refresh Feed", key="refresh_feed"):
            st.session_state.pop("feed_events", None)
            st.rerun()

        if not feed_events:
            st.markdown(
                '<div style="text-align:center;padding:3rem;color:#8B95AD;">'
                ''
                "<div>No activity yet! Complete a workout or add friends to see their activity here.</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            for idx, ev in enumerate(feed_events):
                _event_type_icons = {
                    "activity": "●", "plan": "●", "pb": "●", "hyrox": "●", "milestone": "●",
                }
                icon = _event_type_icons.get(ev.get("event_type", ""), "●")
                user_name = ev.get("user_name", "Unknown")
                _ev_user_id = ev.get("user_id", "")
                initials = "".join(w[0].upper() for w in user_name.split()[:2]) if user_name else "?"
                created = ev.get("created_at", "")[:10]
                like_count = ev.get("like_count", 0)
                comment_count = ev.get("comment_count", 0)
                liked_by_me = ev.get("liked_by_me", False)
                heart = "♥" if liked_by_me else "♡"

                # Parse metadata for rich cards
                _ev_meta_raw = ev.get("metadata")
                _ev_meta = {}
                if _ev_meta_raw:
                    try:
                        _ev_meta = json.loads(_ev_meta_raw) if isinstance(_ev_meta_raw, str) else (_ev_meta_raw or {})
                    except (json.JSONDecodeError, TypeError):
                        _ev_meta = {}

                # Build rich metrics HTML for activity events
                _rich_metrics_html = ""
                if ev.get("event_type") == "activity" and _ev_meta:
                    _m_items = []
                    _m_dist = _ev_meta.get("distance_meters")
                    _m_dur = _ev_meta.get("duration_seconds")
                    _m_pace = _ev_meta.get("avg_pace_sec_per_km")
                    _m_hr = _ev_meta.get("avg_hr")
                    _m_cal = _ev_meta.get("calories")
                    _m_elev = _ev_meta.get("elevation_gain")
                    _m_te = _ev_meta.get("training_effect_aerobic")
                    if _m_dist:
                        _m_items.append(("Distance", f"{_m_dist / 1000:.1f}", "km"))
                    if _m_dur:
                        _dm, _ds = divmod(int(_m_dur), 60)
                        _m_items.append(("Duration", f"{_dm}:{_ds:02d}", ""))
                    if _m_pace:
                        _pm, _ps = divmod(int(_m_pace), 60)
                        _m_items.append(("Pace", f"{_pm}:{_ps:02d}", "/km"))
                    if _m_hr:
                        _m_items.append(("Avg HR", str(int(_m_hr)), "bpm"))
                    if _m_cal:
                        _m_items.append(("Calories", str(int(_m_cal)), ""))
                    if _m_elev and _m_elev > 0:
                        _m_items.append(("Elevation", f"{int(_m_elev)}", "m"))
                    if _m_te:
                        _m_items.append(("Aerobic TE", f"{_m_te:.1f}", ""))
                    if _m_items:
                        _rich_metrics_html = _metrics_strip(_m_items)

                # User name is clickable to view profile
                _name_click_html = (
                    f'<span style="color:#E8ECF4;font-weight:600;cursor:pointer;'
                    f'border-bottom:1px dashed #8B95AD33;">{user_name}</span>'
                )

                st.markdown(
                    f'<div style="background:#161821;border:1px solid #252A35;border-radius:12px;'
                    f'padding:1.2rem;margin-bottom:0.8rem;">'
                    f'<div style="display:flex;align-items:center;gap:0.8rem;margin-bottom:0.6rem;">'
                    f'<div style="width:36px;height:36px;border-radius:50%;background:#10B98133;'
                    f'display:flex;align-items:center;justify-content:center;color:#10B981;'
                    f'font-weight:700;font-size:0.85rem;">{initials}</div>'
                    f'<div>{_name_click_html}'
                    f'<span style="color:#8B95AD;font-size:0.8rem;margin-left:0.5rem;">{created}</span></div>'
                    f'</div>'
                    f'<div style="font-size:1.05rem;color:#E8ECF4;margin-bottom:0.3rem;">'
                    f'{icon} {ev.get("title", "")}</div>'
                    + (f'<div style="color:#B0B7C3;font-size:0.9rem;margin-bottom:0.5rem;">{ev.get("body")}</div>'
                       if ev.get("body") else '')
                    + _rich_metrics_html
                    + f'<div style="color:#8B95AD;font-size:0.85rem;margin-top:0.4rem;">'
                    f'{heart} {like_count}  ·  {comment_count}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Actions row — View Profile + Like + Comment + Strava
                _is_own_activity = (_ev_user_id == st.session_state.get("user_id", ""))
                _feed_act_id = _ev_meta.get("activity_id") if (_is_own_activity and ev.get("event_type") == "activity") else None
                _show_strava_in_feed = False
                if _feed_act_id:
                    _strava_prefs = st.session_state.get("_strava_conn")
                    if _strava_prefs is None:
                        try:
                            _sc = requests.get(f"{API_BASE}/strava/status", headers=_auth_headers(), timeout=5)
                            _strava_prefs = _sc.json() if _sc.status_code == 200 else {"connected": False}
                        except Exception:
                            _strava_prefs = {"connected": False}
                        st.session_state["_strava_conn"] = _strava_prefs
                    _show_strava_in_feed = _strava_prefs.get("connected", False)

                if _show_strava_in_feed:
                    col_profile, col_like, col_comment, col_strava = st.columns([1, 1, 1, 1])
                else:
                    col_profile, col_like, col_comment = st.columns([1, 1, 1])
                    col_strava = None
                with col_profile:
                    if st.button("Profile", key=f"feed_profile_{ev['id']}_{idx}", use_container_width=True):
                        st.session_state["viewing_profile_id"] = _ev_user_id
                        st.rerun()
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
                    if st.button("Comment", key=f"feed_toggle_comment_{ev['id']}_{idx}", use_container_width=True):
                        if st.session_state.get(f"show_comments_{ev['id']}"):
                            st.session_state[f"show_comments_{ev['id']}"] = False
                        else:
                            st.session_state[f"show_comments_{ev['id']}"] = True
                        st.rerun()

                if col_strava is not None and _feed_act_id:
                    with col_strava:
                        _feed_sent = st.session_state.get(f"strava_sent_{_feed_act_id}", False)
                        if _feed_sent:
                            st.markdown('<span style="color:#FC4C02;font-size:0.8rem;">✓ Strava</span>', unsafe_allow_html=True)
                        elif st.button("Strava", key=f"feed_strava_{ev['id']}_{idx}", use_container_width=True):
                            with st.spinner("Sending..."):
                                try:
                                    _sr = requests.post(
                                        f"{API_BASE}/strava/push/{_feed_act_id}",
                                        headers=_auth_headers(), timeout=60,
                                    )
                                    if _sr.status_code == 200 or _sr.status_code == 409:
                                        st.session_state[f"strava_sent_{_feed_act_id}"] = True
                                        st.rerun()
                                    else:
                                        st.error(f"Failed: {_sr.text}")
                                except Exception as _se:
                                    st.error(f"Failed: {_se}")

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
                            f'<div style="margin-left:2rem;padding:0.5rem 0.8rem;border-left:2px solid #252A35;'
                            f'margin-bottom:0.3rem;">'
                            f'<span style="color:#10B981;font-weight:600;font-size:0.85rem;">{c_name}</span>'
                            f'<span style="color:#8B95AD;font-size:0.75rem;margin-left:0.4rem;">{c_date}</span>'
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
        title={"text": title, "font": {"size": 14, "color": "#8B95AD", "family": "Figtree, sans-serif"}},
        number={"font": {"size": 36, "color": "#E8ECF4", "family": "JetBrains Mono, monospace"}},
        gauge={
            "axis": {"range": [range_min, range_max], "tickcolor": "rgba(148,163,194,0.18)", "tickfont": {"color": "#8B95AD"}},
            "bar": {"color": color},
            "bgcolor": "#1C1F2B",
            "borderwidth": 0,
            "steps": steps,
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=220, margin=dict(t=35, b=15, l=25, r=25),
        hoverlabel=dict(bgcolor="#1A1D2B", bordercolor="rgba(148,163,194,0.12)", font=dict(color="#E8ECF4")),
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


def _section_card(title, content_html, accent="#0EA5E9"):
    """Render a section card with accent header."""
    return (
        f'<div style="background:#1A1D2B;border:1px solid rgba(148,163,194,0.12);border-radius:10px;'
        f'padding:16px 18px;margin-bottom:0.75rem;">'
        f'<div style="font-weight:600;color:{accent};margin-bottom:8px;font-size:0.9rem;'
        f'font-family:Manrope,sans-serif;letter-spacing:-0.01em;">{title}</div>'
        f'<div style="color:#8B95AD;font-size:0.85rem;line-height:1.6;">{content_html}</div>'
        f'</div>'
    )


def _bullet_list(items, color="#10B981", icon="▸"):
    """Render a colored bullet list."""
    lines = "".join(
        f'<div style="padding:3px 0;color:#A0A8BE;font-size:0.88rem;">'
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
    p = st.session_state.profile
    if not p:
        st.markdown(_skeleton_cards(3), unsafe_allow_html=True)
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
            "Snapshot", "Aerobic Engine", "Running Economy",
            "Load & Recovery", "Race Predictions",
            "Recommendations", "Trends",
        ])

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 1: ATHLETE SNAPSHOT
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[0]:
            snap = (analytics or {}).get("snapshot", {})
            level = snap.get("fitness_level", "—")
            level_colors = {"Beginner": "#F59E0B", "Intermediate": "#0EA5E9", "Advanced": "#10B981", "Elite": "#FBBF24"}
            level_color = level_colors.get(level, "#8B95AD")

            # Hero card
            vdot_val = snap.get("vdot", "—")
            t_status = snap.get("training_status", "—")
            t_age = snap.get("training_age_estimate", "—")
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1A1D24,#161821);border-radius:12px;'
                f'padding:20px 24px;margin-bottom:1rem;border:1px solid #252A35;">'
                f'<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
                f'<div style="background:{level_color}22;border:2px solid {level_color};border-radius:50%;'
                f'width:64px;height:64px;display:flex;align-items:center;justify-content:center;'
                f'font-size:1.6rem;font-weight:800;color:{level_color};">'
                f'{level[0] if level != "—" else "?"}</div>'
                f'<div>'
                f'<div style="font-size:1.3rem;font-weight:700;color:#E8ECF4;">{level} Athlete</div>'
                f'<div style="color:#8B95AD;font-size:0.85rem;margin-top:2px;">'
                f'Training age: {t_age} · Status: {t_status}</div>'
                f'</div>'
                f'<div style="margin-left:auto;text-align:right;">'
                f'<div style="font-size:2rem;font-weight:800;color:#FBBF24;">'
                f'{vdot_val if vdot_val != "—" else "—"}</div>'
                f'<div style="color:#8B95AD;font-size:0.8rem;">VDOT</div>'
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
                    _section_card("Strengths", _bullet_list(snap.get("strengths", []), "#10B981", "✓"), "#10B981"),
                    unsafe_allow_html=True,
                )
            with sw_col2:
                st.markdown(
                    _section_card("Weaknesses", _bullet_list(snap.get("weaknesses", []), "#F59E0B", "✗"), "#F59E0B"),
                    unsafe_allow_html=True,
                )

            # HR Zone distribution
            zones = p.get("hr_zones", [])
            if zones:
                st.markdown("")
                zone_colors = ["#34D399", "#8BC34A", "#FFC107", "#F59E0B", "#F43F5E"]
                zone_labels = ["Z1", "Z2", "Z3", "Z4", "Z5"]
                zone_names = ["Recovery", "Aerobic", "Tempo", "Threshold", "VO2max"]
                zone_html = '<div style="display:flex;gap:3px;border-radius:10px;overflow:hidden;">'
                for i, z in enumerate(zones[:5]):
                    c = zone_colors[i] if i < len(zone_colors) else "#607D8B"
                    lbl = zone_labels[i] if i < len(zone_labels) else f"Z{i+1}"
                    name = zone_names[i] if i < len(zone_names) else ""
                    bpm_range = f'{z.get("low_bpm","")}-{z.get("high_bpm","")}'
                    zone_html += (
                        f'<div style="flex:1;background:{c}15;border:1px solid {c}25;padding:10px 6px;text-align:center;border-radius:8px;">'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:{c};font-weight:700;">{lbl}</div>'
                        f'<div style="font-size:0.62rem;color:#8B95AD;margin:2px 0;">{name}</div>'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#A0A8BE;">{bpm_range}</div>'
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
                    _gauge_chart(vo2, "VO2 Max", 20, 70, "#10B981", [
                        {"range": [20, 35], "color": "rgba(244,63,94,0.15)"},
                        {"range": [35, 50], "color": "rgba(245,158,11,0.15)"},
                        {"range": [50, 70], "color": "rgba(16,185,129,0.15)"},
                    ], "vo2_aero")
                with gc2:
                    cat = aero.get("vo2max_category", "—")
                    interp = aero.get("vo2max_interpretation", "")
                    st.markdown(
                        f'<div style="padding-top:20px;">'
                        f'{_badge(cat, "#10B981" if cat in ("Superior","Excellent") else "#F59E0B" if cat in ("Good","Fair") else "#F43F5E")}'
                        f'<div style="color:#A0A8BE;font-size:0.88rem;margin-top:12px;line-height:1.6;">{interp}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Aerobic vs Anaerobic balance
            aer_r = aero.get("aerobic_ratio", 0)
            ana_r = aero.get("anaerobic_ratio", 0)
            st.markdown("")
            st.markdown('<div style="font-weight:600;color:#8B95AD;font-size:0.85rem;margin-bottom:6px;">Training Effect Balance</div>', unsafe_allow_html=True)
            aer_pct = round(aer_r * 100)
            ana_pct = round(ana_r * 100)
            st.markdown(
                f'<div style="display:flex;border-radius:8px;overflow:hidden;height:28px;">'
                f'<div style="flex:{aer_pct};background:#0EA5E9;display:flex;align-items:center;justify-content:center;'
                f'font-size:0.75rem;font-weight:600;color:#fff;">{aer_pct}% Aerobic</div>'
                f'<div style="flex:{ana_pct};background:#F43F5E;display:flex;align-items:center;justify-content:center;'
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
                    content += f"<br><span style='color:#8B95AD;font-size:0.8rem;'>LT pace = {thr_pct}% of VDOT pace</span>"
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
                st.markdown(_section_card("Threshold Quality", content, "#F59E0B"), unsafe_allow_html=True)
            with ce_col:
                ce = aero.get("cardiac_efficiency", "—")
                drift = aero.get("cardiac_drift_indicator")
                content = ce
                if drift:
                    content += f"<br><span style='color:#8B95AD;font-size:0.8rem;'>HR/Pace ratio: {drift:.3f}</span>"
                decoup = aero.get("aerobic_decoupling_pct")
                if decoup is not None:
                    content += f"<br><span style='color:#8B95AD;font-size:0.8rem;'>Aerobic decoupling: {decoup:+.1f}%</span>"
                st.markdown(_section_card("Cardiac Efficiency", content, "#F43F5E"), unsafe_allow_html=True)

            # Pace vs HR scatter
            acts = p.get("recent_activities", [])
            scatter_data = [(a["avg_pace_sec_per_km"], a["avg_hr"]) for a in acts
                           if a.get("avg_pace_sec_per_km") and a.get("avg_hr")]
            if scatter_data:
                st.markdown("")
                paces_v, hrs_v = zip(*scatter_data)
                # Format paces as MM:SS for display
                pace_labels = [f"{int(pv)//60}:{int(pv)%60:02d}" for pv in paces_v]
                fig_scatter = go.Figure()
                fig_scatter.add_trace(go.Scatter(
                    x=[pv / 60 for pv in paces_v], y=list(hrs_v),
                    mode="markers",
                    marker=dict(color="#0EA5E9", size=8, opacity=0.7),
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
                fig_scatter.update_layout(**_pf_layout(
                    title="Cardiac Efficiency: Pace vs Heart Rate",
                    xaxis_title="Pace (min/km)", yaxis_title="Avg HR (bpm)",
                    margin=dict(l=50, r=20, t=40, b=40), height=300,
                    xaxis=dict(gridcolor="rgba(148,163,194,0.06)", autorange="reversed",
                               tickvals=tick_vals, ticktext=tick_text, zeroline=False),
                    yaxis=dict(gridcolor="rgba(148,163,194,0.08)", zeroline=False),
                ))
                st.plotly_chart(fig_scatter, use_container_width=True, key="scatter_pace_hr")

        # ═════════════════════════════════════════════════════════════
        # SUB-TAB 3: RUNNING ECONOMY
        # ═════════════════════════════════════════════════════════════
        with prof_tabs[2]:
            econ = (analytics or {}).get("economy", {})
            grade = econ.get("overall_grade", "—")
            grade_colors = {"A": "#10B981", "B": "#0EA5E9", "C": "#F59E0B", "D": "#F43F5E", "—": "#8B95AD"}
            gc = grade_colors.get(grade, "#8B95AD")

            # Grade badge
            st.markdown(
                f'<div style="text-align:center;margin-bottom:1rem;">'
                f'<div style="display:inline-block;background:{gc}22;border:2px solid {gc};border-radius:16px;'
                f'padding:12px 28px;">'
                f'<div style="font-size:2rem;font-weight:800;color:{gc};">{grade}</div>'
                f'<div style="font-size:0.8rem;color:#8B95AD;">Running Economy Grade</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # 4 metric cards
            ec1, ec2, ec3, ec4 = st.columns(4)
            cad = econ.get("cadence_avg")
            with ec1:
                val = f"{cad:.0f}" if cad else "—"
                st.markdown(_metric_card("Cadence", val, "spm", "cyan"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B95AD;">{econ.get("cadence_grade","")}</div>', unsafe_allow_html=True)
            with ec2:
                sl = econ.get("stride_length_avg")
                val = f"{sl:.2f}" if sl else "—"
                st.markdown(_metric_card("Stride Length", val, "m", "blue"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B95AD;">{econ.get("stride_grade","")}</div>', unsafe_allow_html=True)
            with ec3:
                gct = econ.get("gct_avg")
                val = f"{gct:.0f}" if gct else "—"
                st.markdown(_metric_card("Ground Contact", val, "ms", "orange"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B95AD;">{econ.get("gct_grade","")}</div>', unsafe_allow_html=True)
            with ec4:
                vo = econ.get("vert_osc_avg")
                val = f"{vo:.1f}" if vo else "—"
                st.markdown(_metric_card("Vert. Oscillation", val, "cm", "purple"), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center;font-size:0.75rem;color:#8B95AD;">{econ.get("vert_osc_grade","")}</div>', unsafe_allow_html=True)

            # Inefficiency callouts
            ineff = econ.get("inefficiencies", [])
            if ineff:
                st.markdown("")
                st.markdown(
                    _section_card("Key Inefficiencies", _bullet_list(ineff, "#F59E0B", "!"), "#F59E0B"),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown("")
                st.markdown(
                    _section_card("Running Mechanics", "No significant inefficiencies detected. Mechanics look solid.", "#10B981"),
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
                    _gauge_chart(bb, "Body Battery", 0, 100, "#10B981", [
                        {"range": [0, 25], "color": "rgba(244,63,94,0.15)"},
                        {"range": [25, 60], "color": "rgba(245,158,11,0.15)"},
                        {"range": [60, 100], "color": "rgba(16,185,129,0.15)"},
                    ], "body_battery")
                else:
                    st.markdown(_metric_card("Body Battery", "—", "", "green"), unsafe_allow_html=True)
            with lr2:
                ss = p.get("sleep_score")
                if ss and isinstance(ss, (int, float)):
                    _gauge_chart(ss, "Sleep Score", 0, 100, "#8B5CF6", [
                        {"range": [0, 40], "color": "rgba(244,63,94,0.15)"},
                        {"range": [40, 70], "color": "rgba(245,158,11,0.15)"},
                        {"range": [70, 100], "color": "rgba(16,185,129,0.15)"},
                    ], "sleep_score")
                else:
                    st.markdown(_metric_card("Sleep Score", "—", "", "purple"), unsafe_allow_html=True)
            with lr3:
                sa = p.get("stress_avg")
                if sa and isinstance(sa, (int, float)):
                    stress_color = "#10B981" if sa <= 25 else "#F59E0B" if sa <= 50 else "#F43F5E"
                    _gauge_chart(sa, "Avg Stress", 0, 100, stress_color, [
                        {"range": [0, 25], "color": "rgba(16,185,129,0.15)"},
                        {"range": [25, 50], "color": "rgba(245,158,11,0.15)"},
                        {"range": [50, 100], "color": "rgba(244,63,94,0.15)"},
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
                        labels.append("Deep"); vals.append(sleep_deep / 60); colors.append("#0369A1")
                    if sleep_light:
                        labels.append("Light"); vals.append(sleep_light / 60); colors.append("#0EA5E9")
                    if sleep_rem:
                        labels.append("REM"); vals.append(sleep_rem / 60); colors.append("#8B5CF6")
                    if sleep_awake:
                        labels.append("Awake"); vals.append(sleep_awake / 60); colors.append("#F59E0B")
                    fig_sleep = go.Figure(go.Pie(
                        labels=labels, values=vals, marker_colors=colors,
                        hole=0.55, textinfo="label+percent", textfont_size=11,
                        textfont_color="#A0A8BE",
                    ))
                    fig_sleep.update_layout(
                        title=f"Sleep Stages ({sleep_dur / 3600:.1f}h total)",
                        title_font=dict(size=13, color="#8B95AD", family="Figtree, sans-serif"),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Figtree, sans-serif", color="#E8ECF4", size=11),
                        height=280, margin=dict(t=40, b=20, l=20, r=20),
                        legend=dict(font=dict(color="#8B95AD", size=10)),
                        hoverlabel=dict(bgcolor="#1A1D2B", bordercolor="rgba(148,163,194,0.12)", font=dict(color="#E8ECF4")),
                        showlegend=True,
                    )
                    st.plotly_chart(fig_sleep, use_container_width=True, key="sleep_pie")
                else:
                    st.markdown(_section_card("Sleep", "No sleep stage data available", "#8B5CF6"), unsafe_allow_html=True)

            with lr_col2:
                # Load + HRV + Fatigue
                load_status = lr.get("load_status", "—")
                load_colors = {"Optimal": "#10B981", "Recovery": "#0EA5E9", "Overreaching": "#F43F5E",
                               "Undertraining": "#F59E0B", "Unknown": "#8B95AD"}
                lc = load_colors.get(load_status, "#8B95AD")
                tl = lr.get("training_load_7day")
                lf = lr.get("load_focus")
                load_html = f'{_badge(load_status, lc)}'
                if tl:
                    load_html += f'<div style="color:#A0A8BE;font-size:0.85rem;margin-top:8px;">7-day load: {tl:.0f}</div>'
                if lf:
                    load_html += f'<div style="color:#8B95AD;font-size:0.8rem;">Focus: {lf}</div>'
                st.markdown(_section_card("Training Load", load_html, lc), unsafe_allow_html=True)

                hrv_a = lr.get("hrv_assessment", "—")
                hrv_c = {"Stable": "#10B981", "Improving": "#0EA5E9", "Declining": "#F43F5E"}.get(hrv_a, "#8B95AD")
                hrv_html = f'{_badge(hrv_a, hrv_c)}'
                hlv = p.get("hrv_last_night")
                if hlv:
                    hrv_html += f'<span style="color:#A0A8BE;font-size:0.85rem;margin-left:10px;">Last night: {hlv:.0f} ms</span>'
                st.markdown(_section_card("HRV Status", hrv_html, hrv_c), unsafe_allow_html=True)

                fatigue = lr.get("fatigue_risk", "—")
                fat_c = {"Low": "#10B981", "Moderate": "#F59E0B", "High": "#F43F5E"}.get(fatigue, "#8B95AD")
                st.markdown(_section_card("Fatigue Risk", _badge(fatigue, fat_c), fat_c), unsafe_allow_html=True)

            # Recovery tips
            tips = lr.get("recovery_tips", [])
            if tips:
                st.markdown("")
                st.markdown(
                    _section_card("Recovery Tips", _bullet_list(tips, "#8B5CF6", "→"), "#8B5CF6"),
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
                    source_note = f'<span style="color:#10B981;font-size:0.8rem;margin-left:8px;">({garmin_count} from Garmin)</span>'
                st.markdown(
                    f'<div style="text-align:center;margin-bottom:1rem;">'
                    f'<span style="font-size:0.85rem;color:#8B95AD;">Based on </span>'
                    f'<span style="font-size:1.1rem;font-weight:700;color:#FBBF24;">VDOT {rp_vdot}</span>'
                    f'{source_note}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Predictions table
            if preds:
                table_html = (
                    '<div style="background:#161821;border-radius:10px;padding:12px 16px;margin-bottom:1rem;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #252A35;">'
                    '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.8rem;">Distance</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.8rem;">Predicted Time</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.8rem;">Pace/km</th>'
                    '<th style="text-align:right;padding:8px;color:#8B95AD;font-size:0.8rem;">Confidence</th>'
                    '</tr>'
                )
                for pred in preds:
                    time_str = _fmt_time(pred["predicted_seconds"])
                    pm, ps = divmod(int(pred["pace_sec_per_km"]), 60)
                    pace_str = f"{pm}:{ps:02d}"
                    conf = pred["confidence"]
                    conf_c = {"High": "#10B981", "Moderate": "#F59E0B", "Low": "#F43F5E"}.get(conf, "#8B95AD")
                    table_html += (
                        f'<tr style="border-bottom:1px solid #252A3522;">'
                        f'<td style="padding:10px 8px;font-weight:500;color:#E8ECF4;">{pred["distance"]}</td>'
                        f'<td style="padding:10px 8px;text-align:center;color:#10B981;font-weight:600;font-size:1.05rem;">{time_str}</td>'
                        f'<td style="padding:10px 8px;text-align:center;color:#A0A8BE;">{pace_str}/km</td>'
                        f'<td style="padding:10px 8px;text-align:right;">{_badge(conf, conf_c)}</td>'
                        f'</tr>'
                    )
                table_html += '</table></div>'
                st.markdown(table_html, unsafe_allow_html=True)

            # PBs vs Predictions comparison
            pbs = {pr["distance"]: pr["time_seconds"] for pr in p.get("personal_records", [])}
            garmin_preds = {rpp["distance"]: rpp["predicted_seconds"] for rpp in p.get("race_predictions", [])}
            if pbs or garmin_preds:
                st.markdown('<div style="font-weight:600;color:#8B95AD;font-size:0.85rem;margin:8px 0;">Performance Comparison</div>', unsafe_allow_html=True)
                comp_html = '<div style="background:#161821;border-radius:10px;padding:12px 16px;">'
                for pred in preds:
                    dist_key_map = {"Half Marathon": "HALF_MARATHON", "Marathon": "MARATHON", "5K": "5K", "10K": "10K"}
                    nk = dist_key_map.get(pred["distance"], pred["distance"])
                    pb_t = pbs.get(nk)
                    gp_t = garmin_preds.get(nk)
                    if pb_t or gp_t:
                        comp_html += f'<div style="padding:6px 0;border-bottom:1px solid #252A3533;">'
                        comp_html += f'<span style="color:#E8ECF4;font-weight:500;width:120px;display:inline-block;">{pred["distance"]}</span>'
                        comp_html += f'<span style="color:#FBBF24;margin-right:16px;">VDOT: {_fmt_time(pred["predicted_seconds"])}</span>'
                        if gp_t:
                            comp_html += f'<span style="color:#0EA5E9;margin-right:16px;">Garmin: {_fmt_time(gp_t)}</span>'
                        if pb_t:
                            comp_html += f'<span style="color:#10B981;">PB: {_fmt_time(pb_t)}</span>'
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
                    _section_card("Consistency Check", _bullet_list(notes, "#FBBF24", "→"), "#FBBF24"),
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
                    line=dict(color="#F59E0B", width=3),
                    marker=dict(size=10, color="#F59E0B"),
                    fill="tozeroy", fillcolor="rgba(255,152,0,0.1)",
                    hovertemplate="%{x}<br>%{y:.2f} min/km<extra></extra>",
                ))
                fig_fr.update_layout(**_pf_layout(
                    title="Fatigue Resistance Curve (Pace vs Distance)",
                    yaxis_title="Pace (min/km)", yaxis_autorange="reversed",
                    margin=dict(l=50, r=20, t=40, b=40), height=300,
                ))
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
                    sp_colors = ["#0EA5E9", "#F59E0B", "#F43F5E", "#8B5CF6"]
                    fig_split = go.Figure(go.Pie(
                        labels=sp_labels, values=sp_vals,
                        marker_colors=sp_colors[:len(sp_vals)],
                        hole=0.5, textinfo="label+percent", textfont_size=11,
                        textfont_color="#A0A8BE",
                    ))
                    fig_split.update_layout(
                        title="Recommended Training Split",
                        title_font=dict(size=13, color="#8B95AD", family="Figtree, sans-serif"),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Figtree, sans-serif", color="#E8ECF4", size=11),
                        height=280, margin=dict(t=40, b=10, l=10, r=10),
                        legend=dict(font=dict(color="#8B95AD", size=10)),
                        hoverlabel=dict(bgcolor="#1A1D2B", bordercolor="rgba(148,163,194,0.12)", font=dict(color="#E8ECF4")),
                    )
                    st.plotly_chart(fig_split, use_container_width=True, key="training_split")

                with rc2:
                    # HYROX progression
                    hyrox_prog = rec.get("hyrox_progression", [])
                    if hyrox_prog:
                        st.markdown(
                            _section_card("HYROX Progression", _bullet_list(hyrox_prog, "#F59E0B", "→"), "#F59E0B"),
                            unsafe_allow_html=True,
                        )
                    # Recovery optimization
                    rec_opt = rec.get("recovery_optimization", [])
                    if rec_opt:
                        st.markdown(
                            _section_card("Recovery Optimization", _bullet_list(rec_opt, "#8B5CF6", "→"), "#8B5CF6"),
                            unsafe_allow_html=True,
                        )

            # Key sessions table
            sessions = rec.get("key_sessions", [])
            if sessions:
                st.markdown("")
                st.markdown('<div style="font-weight:600;color:#8B95AD;font-size:0.85rem;margin-bottom:6px;">Key Sessions</div>', unsafe_allow_html=True)
                sess_html = (
                    '<div style="background:#161821;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #252A35;">'
                    '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.78rem;">Session</th>'
                    '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.78rem;">Description</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Pace</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">HR</th>'
                    '</tr>'
                )
                session_colors = ["#F43F5E", "#F59E0B", "#0EA5E9", "#8B5CF6", "#10B981"]
                for i, s in enumerate(sessions):
                    sc = session_colors[i % len(session_colors)]
                    sess_html += (
                        f'<tr style="border-bottom:1px solid #252A3522;">'
                        f'<td style="padding:8px;color:{sc};font-weight:600;font-size:0.88rem;">{s["name"]}</td>'
                        f'<td style="padding:8px;color:#A0A8BE;font-size:0.85rem;">{s["description"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FBBF24;font-size:0.85rem;">{s["pace_target"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#F43F5E;font-size:0.85rem;">{s["hr_target"]}</td>'
                        f'</tr>'
                    )
                sess_html += '</table></div>'
                st.markdown(sess_html, unsafe_allow_html=True)

            # Progress benchmarks table
            benchmarks = rec.get("benchmarks", [])
            if benchmarks:
                st.markdown("")
                st.markdown('<div style="font-weight:600;color:#8B95AD;font-size:0.85rem;margin-bottom:6px;">Progress Benchmarks</div>', unsafe_allow_html=True)
                bench_html = (
                    '<div style="background:#161821;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #252A35;">'
                    '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.78rem;">Metric</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Current</th>'
                    '<th style="text-align:center;padding:8px;color:#0EA5E9;font-size:0.78rem;">4 Weeks</th>'
                    '<th style="text-align:center;padding:8px;color:#F59E0B;font-size:0.78rem;">8 Weeks</th>'
                    '<th style="text-align:center;padding:8px;color:#10B981;font-size:0.78rem;">12 Weeks</th>'
                    '</tr>'
                )
                for b in benchmarks:
                    bench_html += (
                        f'<tr style="border-bottom:1px solid #252A3522;">'
                        f'<td style="padding:8px;color:#E8ECF4;font-weight:500;">{b["metric"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#A0A8BE;">{b["current"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#0EA5E9;">{b["target_4wk"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#F59E0B;">{b["target_8wk"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#10B981;">{b["target_12wk"]}</td>'
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

                chart_layout = _pf_layout()

                trend_col1, trend_col2 = st.columns(2)

                paces_list = [a.get("avg_pace_sec_per_km") for a in sorted_acts]
                if any(pv is not None for pv in paces_list):
                    with trend_col1:
                        pace_vals, pace_dates, pace_labels_t = [], [], []
                        for d, pv in zip(dates, paces_list):
                            if pv and pv > 0:
                                pace_vals.append(pv / 60)
                                pace_dates.append(d)
                                pace_labels_t.append(f"{int(pv)//60}:{int(pv)%60:02d}")
                        fig_pace = go.Figure()
                        fig_pace.add_trace(go.Scatter(
                            x=pace_dates, y=pace_vals,
                            mode="lines+markers",
                            line=dict(color="#10B981", width=2), marker=dict(size=5),
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
                        for d, hv in zip(dates, hr_list):
                            if hv and hv > 0:
                                hr_vals.append(hv)
                                hr_dates.append(d)
                        fig_hr = go.Figure()
                        fig_hr.add_trace(go.Scatter(
                            x=hr_dates, y=hr_vals,
                            mode="lines+markers",
                            line=dict(color="#F43F5E", width=2), marker=dict(size=5),
                            hovertemplate="%%{x}<br>%%{y} bpm<extra></extra>",
                        ))
                        fig_hr.update_layout(title="Average Heart Rate", yaxis_title="bpm", **chart_layout)
                        st.plotly_chart(fig_hr, use_container_width=True, key="trend_hr")

                trend_col3, trend_col4 = st.columns(2)

                cadence_list = [a.get("avg_running_cadence") for a in sorted_acts]
                if any(cv is not None for cv in cadence_list):
                    with trend_col3:
                        cad_vals, cad_dates = [], []
                        for d, cv in zip(dates, cadence_list):
                            if cv and cv > 0:
                                cad_vals.append(cv)
                                cad_dates.append(d)
                        fig_cad = go.Figure()
                        fig_cad.add_trace(go.Scatter(
                            x=cad_dates, y=cad_vals,
                            mode="lines+markers",
                            line=dict(color="#0EA5E9", width=2), marker=dict(size=5),
                            hovertemplate="%%{x}<br>%%{y:.0f} spm<extra></extra>",
                        ))
                        fig_cad.update_layout(title="Running Cadence", yaxis_title="spm", **chart_layout)
                        st.plotly_chart(fig_cad, use_container_width=True, key="trend_cadence")

                vo2_list = [a.get("vo2_max_value") for a in sorted_acts]
                if any(v is not None for v in vo2_list):
                    with trend_col4:
                        vo2_vals, vo2_dates = [], []
                        for d, vv in zip(dates, vo2_list):
                            if vv and vv > 0:
                                vo2_vals.append(vv)
                                vo2_dates.append(d)
                        fig_vo2t = go.Figure()
                        fig_vo2t.add_trace(go.Scatter(
                            x=vo2_dates, y=vo2_vals,
                            mode="lines+markers",
                            line=dict(color="#F59E0B", width=2), marker=dict(size=5),
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
                        for i, (d, av, nv) in enumerate(zip(dates, te_aer, te_ana)):
                            if av:
                                ta_vals.append(av); ta_dates.append(d)
                            if nv:
                                tn_vals.append(nv); tn_dates.append(d)
                        if ta_vals:
                            fig_te.add_trace(go.Scatter(
                                x=ta_dates, y=ta_vals, name="Aerobic",
                                mode="lines+markers",
                                line=dict(color="#0EA5E9", width=2), marker=dict(size=4),
                            ))
                        if tn_vals:
                            fig_te.add_trace(go.Scatter(
                                x=tn_dates, y=tn_vals, name="Anaerobic",
                                mode="lines+markers",
                                line=dict(color="#F43F5E", width=2), marker=dict(size=4),
                            ))
                        fig_te.update_layout(title="Training Effect", yaxis_title="TE", **chart_layout)
                        st.plotly_chart(fig_te, use_container_width=True, key="trend_te")

                dist_list = [a.get("distance_meters") for a in sorted_acts]
                if any(d is not None for d in dist_list):
                    with trend_col6:
                        d_vals, d_dates = [], []
                        for d, dv in zip(dates, dist_list):
                            if dv and dv > 0:
                                d_vals.append(dv / 1000)
                                d_dates.append(d)
                        fig_dist = go.Figure()
                        fig_dist.add_trace(go.Bar(
                            x=d_dates, y=d_vals,
                            marker_color="#8B5CF6",
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
        "5K": {"icon": "→", "desc": "Speed-focused plan with VO2max intervals and short speed work. Great for building a fast base.", "weeks": "8-12 weeks"},
        "10K": {"icon": "→", "desc": "Balanced plan mixing threshold runs with VO2max work. Builds both speed and endurance.", "weeks": "10-14 weeks"},
        "HALF_MARATHON": {"icon": "→", "desc": "Endurance plan with progressive long runs up to 22km and tempo sessions.", "weeks": "12-16 weeks"},
        "MARATHON": {"icon": "→", "desc": "Full endurance program building to 35km long runs with race-pace specifics.", "weeks": "14-20 weeks"},
        "HYROX": {"icon": "→", "desc": "Hybrid running + functional fitness plan simulating Hyrox race format.", "weeks": "10-14 weeks"},
    }

    with st.expander("Plan Builder" if has_plan else "Create Your Training Plan", expanded=not has_plan):
        step = st.session_state.wizard_step
        wd = st.session_state.wizard_data

        # Progress indicator
        step_labels = ["Goal", "Timeline", "Schedule", "Experience", "Review"]
        progress_html = '<div style="display:flex;gap:4px;margin-bottom:1.2rem;">'
        for i, label in enumerate(step_labels, 1):
            if i < step:
                bg, fg = "#10B981", "#fff"
            elif i == step:
                bg, fg = "#2563EB", "#fff"
            else:
                bg, fg = "#2A2D35", "#8B95AD"
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
                '<p style="font-size:1rem;color:#A0A8BE;margin-bottom:0.5rem;">'
                'What race are you training for? This determines the plan structure, '
                'workout types, and volume progression.</p>',
                unsafe_allow_html=True,
            )
            cols = st.columns(len(GOAL_INFO))
            for i, (goal_key, info) in enumerate(GOAL_INFO.items()):
                with cols[i]:
                    selected = wd.get("goal_type") == goal_key
                    border = "2px solid #10B981" if selected else "1px solid #2A2D35"
                    st.markdown(
                        f'<div style="border:{border};border-radius:10px;padding:12px;text-align:center;min-height:120px;">'
                        f'<div style="font-size:1.5rem;">{info["icon"]}</div>'
                        f'<div style="font-weight:700;margin:4px 0;">{goal_key.replace("_"," ")}</div>'
                        f'<div style="font-size:0.7rem;color:#8B95AD;">{info["weeks"]}</div>'
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
                '<p style="font-size:1rem;color:#A0A8BE;margin-bottom:0.5rem;">'
                'When is your race, and when do you want to start training? '
                'The plan will automatically periodize phases (Base → Build → Peak → Taper) '
                'across the available weeks.</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                target_date = st.date_input(
                    "Race Date",
                    value=wd.get("target_date", date.today() + timedelta(weeks=14)),
                    min_value=date.today() + timedelta(weeks=6),
                    key="wiz_race_date",
                )
            with col2:
                default_start = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
                start_date = st.date_input(
                    "Plan Start Date",
                    value=wd.get("start_date", default_start),
                    min_value=date.today(),
                    max_value=target_date - timedelta(weeks=4),
                    key="wiz_start_date",
                )
            weeks_avail = (target_date - start_date).days // 7
            st.markdown(
                f'<p style="color:#10B981;font-weight:600;">{weeks_avail} weeks of training available</p>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<p style="font-size:1rem;color:#A0A8BE;margin-top:1rem;">'
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
                '<p style="font-size:1rem;color:#A0A8BE;margin-bottom:0.5rem;">'
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
                "Long Run Day",
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
                '<p style="font-size:1rem;color:#A0A8BE;margin-bottom:0.5rem;">'
                'What is your running experience? This affects training volume and intensity:</p>',
                unsafe_allow_html=True,
            )
            exp_info = {
                "beginner": ("→", "Running for less than a year or first-time racer. Lower volume, gentler progression, more recovery."),
                "intermediate": ("→", "1-3 years of consistent running with some race experience. Moderate volume with structured quality sessions."),
                "advanced": ("→", "3+ years of structured training with multiple race finishes. Higher volume, aggressive periodization."),
            }
            for level, (icon, desc) in exp_info.items():
                selected = wd.get("experience") == level
                border = "2px solid #10B981" if selected else "1px solid #2A2D35"
                st.markdown(
                    f'<div style="border:{border};border-radius:10px;padding:12px 16px;margin-bottom:8px;">'
                    f'<span style="font-size:1.2rem;">{icon}</span> '
                    f'<strong>{level.capitalize()}</strong>'
                    f'<span style="color:#8B95AD;font-size:0.85rem;margin-left:8px;">{desc}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Select {level.capitalize()}", key=f"exp_{level}", use_container_width=True):
                    wd["experience"] = level
                    st.session_state.wizard_step = 5
                    st.rerun()

            with st.expander("Custom Paces (optional)", expanded=False):
                st.markdown(
                    '<p style="font-size:0.85rem;color:#8B95AD;">'
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
                '<p style="font-size:1rem;color:#A0A8BE;margin-bottom:0.5rem;">'
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
                f'<div style="background:#161821;border-radius:10px;padding:16px;margin-bottom:1rem;">'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
                f'<div><span style="color:#8B95AD;font-size:0.8rem;">GOAL</span><br/>'
                f'<span style="font-weight:700;font-size:1.1rem;">{goal_info.get("icon","")} {wd.get("goal_type","").replace("_"," ")}</span></div>'
                f'<div><span style="color:#8B95AD;font-size:0.8rem;">RACE DATE</span><br/>'
                f'<span style="font-weight:700;">{td.strftime("%b %d, %Y")}</span></div>'
                f'<div><span style="color:#8B95AD;font-size:0.8rem;">TRAINING WEEKS</span><br/>'
                f'<span style="font-weight:700;">{weeks_avail} weeks ({sd.strftime("%b %d")} → {td.strftime("%b %d")})</span></div>'
                f'<div><span style="color:#8B95AD;font-size:0.8rem;">TARGET TIME</span><br/>'
                f'<span style="font-weight:700;">{target_str}</span></div>'
                f'<div><span style="color:#8B95AD;font-size:0.8rem;">EXPERIENCE</span><br/>'
                f'<span style="font-weight:700;">{wd.get("experience","intermediate").capitalize()}</span></div>'
                f'<div><span style="color:#8B95AD;font-size:0.8rem;">TRAINING DAYS</span><br/>'
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
                if st.button("Generate Plan", type="primary", use_container_width=True, key="wiz_generate"):
                    with st.spinner("Generating your personalised plan..."):
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
                            timeout=300,
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
        status_color = "#10B981" if accepted else "#F59E0B"
        status_text = "✓ Added to Calendar" if accepted else "Draft — Review & Accept"

        goal_icon = GOAL_INFO.get(goal_type, {}).get("icon", "")
        st.markdown(
            f'<div style="background:#161821;border-radius:10px;padding:16px;margin-bottom:0.75rem;">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
            f'<div>'
            f'<div style="font-size:1.2rem;font-weight:700;">{goal_icon} {plan_name}</div>'
            f'<div style="color:#8B95AD;font-size:0.8rem;margin-top:2px;">'
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
        with st.expander("Plan Intelligence", expanded=(p_idx == len(st.session_state.plans) - 1)):
            # Athlete profile data used
            if athlete_summary or pace_source:
                summary_parts = []
                if plan_vdot:
                    summary_parts.append(f'<span style="color:#FBBF24;font-weight:600;">VDOT {plan_vdot:.1f}</span>')
                if pace_source:
                    summary_parts.append(f'<span style="color:#8B95AD;">Paces from: {pace_source}</span>')
                st.markdown(
                    f'<div style="background:#1A1D2B;border:1px solid rgba(251,191,36,0.15);border-radius:10px;padding:14px 18px;'
                    f'margin-bottom:1rem;">'
                    f'<div style="font-weight:600;color:#FBBF24;margin-bottom:6px;font-family:Manrope,sans-serif;">Athlete Data Used</div>'
                    f'<div style="color:#A0A8BE;font-size:0.85rem;line-height:1.6;">'
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
                            f'<div style="padding:3px 0;color:#A0A8BE;font-size:0.85rem;">'
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
                    f'<div style="background:#1A1D2B;border:1px solid rgba(14,165,233,0.15);border-radius:10px;padding:14px 18px;'
                    f'margin-bottom:1rem;">'
                    f'<div style="font-weight:600;color:#0EA5E9;margin-bottom:4px;font-family:Manrope,sans-serif;">Plan Rationale</div>'
                    f'<div style="color:#A0A8BE;font-size:0.9rem;">{rationale}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if tips:
                st.markdown(
                    '<div style="font-weight:600;color:#10B981;margin-bottom:8px;">Personalised Tips</div>',
                    unsafe_allow_html=True,
                )
                for tip in tips:
                    st.markdown(
                        f'<div style="padding:6px 0 6px 16px;border-left:2px solid #2A2D35;'
                        f'color:#A0A8BE;font-size:0.9rem;margin-bottom:4px;">{tip}</div>',
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
            if st.button("Delete Plan", use_container_width=True, key=f"delete_{plan_id}"):
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
                color = _PACE_COLORS.get(zone, "#10B981")
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
            phase_bg = _PHASE_COLORS.get(phase, "rgba(16,185,129,0.12)")
            phase_color = _PHASE_TEXT.get(phase, "#10B981")
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

                # Build day dots summary
                _day_names = ["M", "T", "W", "T", "F", "S", "S"]
                _active_days: dict[int, str] = {}
                for w_item in week.get("workouts", []):
                    sd = w_item.get("scheduled_date", "")
                    wt = w_item.get("workout_type", "rest")
                    if sd and wt != "rest":
                        try:
                            dow = date.fromisoformat(sd).weekday()
                            _active_days[dow] = _WORKOUT_COLORS.get(wt, "#607D8B")
                        except ValueError:
                            pass

                dots_html = '<div class="pf-day-dots">'
                for di, dl in enumerate(_day_names):
                    if di in _active_days:
                        dots_html += f'<div class="pf-day-letter active" style="background:{_active_days[di]};color:#0F1117;">{dl}</div>'
                    else:
                        dots_html += f'<div class="pf-day-letter">{dl}</div>'
                dots_html += '</div>'
                st.markdown(dots_html, unsafe_allow_html=True)

                for w_idx, w in enumerate(week.get("workouts", [])):
                    wtype = w.get("workout_type", "rest")
                    color = _WORKOUT_COLORS.get(wtype, "#607D8B")

                    if wtype == "rest":
                        _sched = w.get("scheduled_date", "")
                        try:
                            _day_lbl = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][date.fromisoformat(_sched).weekday()] if _sched else ""
                        except ValueError:
                            _day_lbl = ""
                        st.markdown(
                            f'<div class="pf-workout-item">'
                            f'<div class="pf-workout-dot" style="background:#6B7280;"></div>'
                            f'<div class="pf-workout-info">'
                            f'<div class="pf-workout-name" style="color:#8B95AD;">'
                            f'{_day_lbl} — Rest Day'
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
                        _sched = w.get("scheduled_date", "")
                        try:
                            _day_lbl = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][date.fromisoformat(_sched).weekday()] if _sched else ""
                        except ValueError:
                            _day_lbl = ""

                        st.markdown(
                            f'<div class="pf-workout-item">'
                            f'<div class="pf-workout-dot" style="background:{color};"></div>'
                            f'<div class="pf-workout-info">'
                            f'<div class="pf-workout-name">'
                            f'{_day_lbl} — {w["name"]}'
                            f'</div>'
                            f'<div class="pf-workout-detail">{detail}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                        with st.expander(f"{w['name']} — Workout Structure", expanded=False):
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

    # Refresh button for calendar tab (reloads data without full page refresh)
    if st.button("Refresh Calendar", key="refresh_calendar_tab"):
        for _rk in ("garmin_activities", "garmin_scheduled", "cal_selected_event", "cal_selected_detail"):
            st.session_state.pop(_rk, None)
        try:
            _rc = requests.get(f"{API_BASE}/activities?days=240&sync=false", headers=_auth_headers(), timeout=15)
            if _rc.status_code == 200:
                st.session_state["garmin_activities"] = _rc.json()
        except Exception:
            pass
        try:
            _rp = requests.get(f"{API_BASE}/plans", headers=_auth_headers(), timeout=10)
            if _rp.status_code == 200:
                st.session_state.plans = _rp.json()
        except Exception:
            pass
        if st.session_state.garmin_logged_in:
            try:
                _rs = requests.get(f"{API_BASE}/garmin/scheduled-workouts", headers=_auth_headers(), timeout=15)
                if _rs.status_code == 200:
                    st.session_state["garmin_scheduled"] = _rs.json()
            except Exception:
                pass
        st.rerun()

    if True:
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

            _act_type = act.get("activity_type", "running")
            _is_cardio = _act_type not in ("running", "trail_running", "treadmill_running")
            if _is_cardio:
                _dur_s = act.get("duration_seconds", 0)
                _dur_m, _dur_sec = divmod(int(_dur_s), 60)
                _cal_title = f"✓ {act.get('name', 'Activity')} ({_dur_m}:{_dur_sec:02d})"
                _cal_bg = "#A78BFA"
            else:
                _cal_title = f"✓ {act.get('name', 'Activity')} ({dist}km{pace_str})"
                _cal_bg = "#10B981"

            cal_events.append({
                "id": f"act_{i}",
                "title": _cal_title,
                "start": start_date,
                "allDay": True,
                "backgroundColor": _cal_bg,
                "borderColor": _cal_bg,
                "editable": False,
                "extendedProps": {
                    "source": "garmin",
                    "activity_id": act.get("activity_id"),
                    "activity_type": act.get("activity_type", "running"),
                    "distance_km": dist,
                    "pace": pace_str,
                    "duration_seconds": act.get("duration_seconds", 0),
                    "avg_hr": act.get("avg_hr"),
                },
            })

        # ── Scheduled workouts from Garmin calendar ──
        for i, sw in enumerate(st.session_state.get("garmin_scheduled", [])):
            sw_date = sw.get("scheduled_date", "")
            sw_name = sw.get("name", "Workout")
            sw_dur = sw.get("estimated_duration_seconds")
            sw_dist = sw.get("estimated_distance_meters")
            _parts = []
            if sw_dist and sw_dist > 0:
                _parts.append(f"{sw_dist / 1000:.1f}km")
            if sw_dur and sw_dur > 0:
                _dm, _ds = divmod(int(sw_dur), 60)
                _parts.append(f"{_dm}:{_ds:02d}")
            _detail = f" ({', '.join(_parts)})" if _parts else ""
            _sport = sw.get("sport_type", "")
            _sw_color = "#60A5FA"  # Blue for Garmin scheduled
            cal_events.append({
                "id": f"garmin_sched_{i}",
                "title": f"📅 {sw_name}{_detail}",
                "start": sw_date,
                "allDay": True,
                "backgroundColor": _sw_color,
                "borderColor": _sw_color,
                "editable": False,
                "extendedProps": {
                    "source": "garmin_scheduled",
                    "name": sw_name,
                    "description": sw.get("description", ""),
                    "sport_type": _sport,
                    "estimated_duration_seconds": sw_dur or 0,
                    "estimated_distance_meters": sw_dist or 0,
                },
            })

        # ── Planned workouts from all plans (accepted shown solid, pending shown muted) ──
        for plan in st.session_state.plans:
            _plan_accepted = plan.get("accepted", False)
            plan_id = plan.get("plan_id", "")
            for week in plan.get("weeks", []):
                for j, w in enumerate(week.get("workouts", [])):
                    wtype = w.get("workout_type", "rest")
                    if wtype == "rest":
                        continue
                    dist = round(w.get("estimated_distance_meters", 0) / 1000, 1)
                    is_completed = w.get("completed", False)
                    prefix = "✓" if is_completed else ("—" if _plan_accepted else "○")
                    if is_completed:
                        bg_color = "#10B981"
                    elif not _plan_accepted:
                        bg_color = "#3E4455"  # Muted for pending plans
                    else:
                        bg_color = _WORKOUT_COLORS.get(wtype, "#607D8B")
                    cal_events.append({
                        "id": f"plan_w{week['week_number']}_{j}",
                        "title": f"{prefix} {w['name']} ({dist}km)",
                        "start": w.get("scheduled_date", ""),
                        "allDay": True,
                        "backgroundColor": bg_color,
                        "borderColor": bg_color,
                        "editable": _plan_accepted and not is_completed,
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
                '<p style="color:#8B95AD;text-align:center;margin:0 0 0.5rem 0;font-size:0.85rem;">'
                'Sync activities from Garmin or generate a training plan to populate the calendar.</p>',
                unsafe_allow_html=True,
            )

        if True:
            # Legend + push controls row (only when events exist)
            if cal_events:
                legend_cols = st.columns([3, 1, 1])
                with legend_cols[0]:
                    st.markdown(
                        '<div style="display:flex;flex-wrap:wrap;gap:1rem;margin-bottom:0.5rem;font-size:0.8rem;">'
                        '<span style="color:#10B981;">● Completed</span>'
                        '<span style="color:#A78BFA;">● Cardio/HIIT</span>'
                        '<span style="color:#60A5FA;">● Garmin Scheduled</span>'
                        '<span style="color:#0EA5E9;">● Long Run</span>'
                        '<span style="color:#34D399;">● Easy</span>'
                        '<span style="color:#F59E0B;">● Tempo</span>'
                        '<span style="color:#F43F5E;">● Speed</span>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    if plan and plan.get("accepted", False):
                        st.caption("Drag planned workouts to reschedule · Click any event for details")
                with legend_cols[1]:
                    if plan and plan.get("accepted", False):
                        if st.button("AI Review Plan", key="cal_ai_review_btn", use_container_width=True):
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
                                        st.success(f"Pushed {data.get('workouts_pushed', '?')} workouts to Garmin!")
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
                    .fc { background: #0F1117; color: #E8ECF4; border: none; }
                    .fc-theme-standard td, .fc-theme-standard th { border-color: #252A35; }
                    .fc-theme-standard .fc-scrollgrid { border-color: #252A35; }
                    .fc-col-header-cell { background: #1A1D2B; }
                    .fc-col-header-cell-cushion { color: #8B95AD; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
                    .fc-daygrid-day-number { color: #8B95AD; font-size: 0.8rem; }
                    .fc-day-today { background: rgba(0,210,106,0.06) !important; }
                    .fc-event { cursor: pointer; font-size: 0.72em; border-radius: 5px; padding: 1px 4px; border: none !important; }
                    .fc-event-title { font-weight: 600; }
                    .fc-button { background: #1A1D2B !important; border: 1px solid #2E3448 !important; color: #E8ECF4 !important; font-size: 0.8rem !important; }
                    .fc-button:hover { background: #252A35 !important; }
                    .fc-button-active { background: #10B981 !important; color: #0F1117 !important; border-color: #10B981 !important; }
                    .fc-toolbar-title { font-size: 1rem !important; font-weight: 700; color: #E8ECF4; }
                """

                from streamlit_calendar import calendar as st_calendar

                _cal_key = f"plan_calendar_{len(cal_events)}"
                result = st_calendar(
                    events=cal_events,
                    options=cal_options,
                    custom_css=cal_css,
                    key=_cal_key,
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
                        with st.spinner("Loading activity details..."):
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
                        '<div style="display:flex;align-items:center;justify-content:center;height:400px;color:#8B95AD;text-align:center;">'
                        '<div><div style="font-size:1rem;margin-bottom:0.5rem;color:#5C6478;">↑</div>'
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
                            f'<div style="color:#8B95AD;font-size:0.8rem;margin-bottom:0.5rem;">{ev_date}</div>',
                            unsafe_allow_html=True,
                        )
                        detail_data = st.session_state.get("cal_selected_detail")
                        if detail_data:
                            _render_garmin_activity_detail(detail_data, activity_type=props.get("activity_type", "running"))
                        else:
                            # Fallback: show basic info from event props
                            dur = props.get("duration_seconds", 0)
                            dur_m, dur_s = divmod(int(dur), 60)
                            dist_km = props.get("distance_km", 0)
                            pace_str = props.get("pace", "")
                            hr_text = f" · Avg HR: {props['avg_hr']} bpm" if props.get("avg_hr") else ""
                            _fb_type = props.get("activity_type", "running")
                            _fb_is_run = _fb_type in ("running", "trail_running", "treadmill_running")
                            if _fb_is_run:
                                _fb_info = f"{dist_km}km · {dur_m}:{dur_s:02d}{pace_str}{hr_text}"
                            else:
                                _fb_info = f"{dur_m}:{dur_s:02d}{hr_text}"
                            st.markdown(
                                f'<div class="pf-card">'
                                f'<div style="color:#E8ECF4;">{_fb_info}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                        # ── AI Analysis for Garmin activities ──
                        _ai_act_id = props.get("activity_id")
                        if _ai_act_id:
                            _cached_analysis = st.session_state.get(f"ai_analysis_{_ai_act_id}")
                            if _cached_analysis:
                                st.markdown(
                                    f'<div class="pf-card" style="margin-top:0.5rem;border:1px solid rgba(16,185,129,0.15);">'
                                    f'<div style="color:#10B981;font-size:0.7rem;font-weight:600;margin-bottom:0.25rem;">AI ANALYSIS</div>'
                                    f'<div style="color:#E8ECF4;font-size:0.82rem;">{_cached_analysis}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                if st.button("Analyze with AI", key=f"garmin_analyze_{_ai_act_id}", use_container_width=True):
                                    with st.spinner("AI is analyzing your activity..."):
                                        try:
                                            r = requests.post(
                                                f"{API_BASE}/activities/{_ai_act_id}/analyze",
                                                headers=_auth_headers(),
                                                timeout=60,
                                            )
                                            if r.status_code == 200:
                                                result = r.json()
                                                st.session_state[f"ai_analysis_{_ai_act_id}"] = result.get("analysis", "")
                                                st.rerun()
                                            else:
                                                st.error(f"Analysis failed: {r.text}")
                                        except Exception as _ai_err:
                                            st.error(f"Analysis failed: {_ai_err}")

                            # ── Send to Strava button ──
                            _strava_prefs = st.session_state.get("_strava_conn")
                            if _strava_prefs is None:
                                try:
                                    _sc = requests.get(f"{API_BASE}/strava/status", headers=_auth_headers(), timeout=5)
                                    _strava_prefs = _sc.json() if _sc.status_code == 200 else {"connected": False}
                                except Exception:
                                    _strava_prefs = {"connected": False}
                                st.session_state["_strava_conn"] = _strava_prefs

                            if _strava_prefs.get("connected"):
                                _already_sent = st.session_state.get(f"strava_sent_{_ai_act_id}", False)
                                if _already_sent:
                                    st.markdown(
                                        '<div style="color:#FC4C02;font-size:0.85rem;padding:0.4rem 0;">'
                                        '✓ Sent to Strava</div>',
                                        unsafe_allow_html=True,
                                    )
                                elif st.button("Send to Strava", key=f"strava_push_{_ai_act_id}", use_container_width=True):
                                    with st.spinner("Sending to Strava..."):
                                        try:
                                            _sr = requests.post(
                                                f"{API_BASE}/strava/push/{_ai_act_id}",
                                                headers=_auth_headers(),
                                                timeout=60,
                                            )
                                            if _sr.status_code == 200:
                                                _sdata = _sr.json()
                                                st.session_state[f"strava_sent_{_ai_act_id}"] = True
                                                if _sdata.get("duplicate"):
                                                    st.info("Activity already exists on Strava (auto-synced from Garmin)")
                                                elif _sdata.get("updated"):
                                                    st.success("Activity enhanced on Strava with PaceForge data!")
                                                    st.markdown(
                                                        f'<a href="{_sdata.get("url", "")}" target="_blank" '
                                                        f'style="color:#FC4C02;">View on Strava</a>',
                                                        unsafe_allow_html=True,
                                                    )
                                                else:
                                                    st.success("Activity posted to Strava!")
                                                    st.markdown(
                                                        f'<a href="{_sdata.get("url", "")}" target="_blank" '
                                                        f'style="color:#FC4C02;">View on Strava</a>',
                                                        unsafe_allow_html=True,
                                                    )
                                            elif _sr.status_code == 409:
                                                st.session_state[f"strava_sent_{_ai_act_id}"] = True
                                                st.info("Already sent to Strava")
                                            else:
                                                st.error(f"Strava push failed: {_sr.text}")
                                        except Exception as _se:
                                            st.error(f"Strava push failed: {_se}")

                    elif props.get("source") == "garmin_scheduled":
                        # Garmin scheduled workout detail
                        sw_name = props.get("name", ev_title)
                        sw_desc = props.get("description", "")
                        sw_dur = props.get("estimated_duration_seconds", 0)
                        sw_dist = props.get("estimated_distance_meters", 0)
                        sw_sport = props.get("sport_type", "")
                        st.markdown(
                            f'<div style="font-weight:700;font-size:1rem;margin-bottom:0.25rem;">📅 {sw_name}</div>'
                            f'<div style="color:#8B95AD;font-size:0.8rem;margin-bottom:0.5rem;">{ev_date} · Garmin Calendar</div>',
                            unsafe_allow_html=True,
                        )
                        _sw_metrics = []
                        if sw_dist and sw_dist > 0:
                            _sw_metrics.append(("Distance", f"{sw_dist / 1000:.1f}km", ""))
                        if sw_dur and sw_dur > 0:
                            _sw_metrics.append(("Duration", _fmt_duration(sw_dur), ""))
                        if sw_sport:
                            _sw_metrics.append(("Sport", sw_sport.replace("_", " ").title(), ""))
                        if _sw_metrics:
                            st.markdown(_metrics_strip(_sw_metrics), unsafe_allow_html=True)
                        if sw_desc:
                            st.markdown(
                                f'<div class="pf-card" style="margin-top:0.5rem;">'
                                f'<div style="color:#8B95AD;font-size:0.7rem;font-weight:600;margin-bottom:0.25rem;">DESCRIPTION</div>'
                                f'<div style="color:#E8ECF4;font-size:0.85rem;white-space:pre-wrap;">{sw_desc}</div>'
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
                                '<div style="background:#1B3A2A;border:1px solid #10B981;border-radius:8px;padding:0.5rem 0.75rem;margin-bottom:0.5rem;">'
                                '<span style="color:#10B981;font-weight:700;">✓ Completed</span></div>',
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            _render_workout_detail(workout_dict, plan_paces),
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="color:#8B95AD;font-size:0.75rem;margin-top:0.5rem;">Scheduled: {ev_date}</div>',
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

                            card_data = []
                            if act_dist:
                                card_data.append(("Distance", f"{act_dist/1000:.1f}", "km"))
                            if act_dur:
                                dm, ds = divmod(int(act_dur), 60)
                                card_data.append(("Duration", f"{dm}:{ds:02d}", ""))
                            if act_pace:
                                pm, ps = divmod(int(act_pace), 60)
                                card_data.append(("Avg Pace", f"{pm}:{ps:02d}/km", ""))
                            if act_hr:
                                card_data.append(("Avg HR", f"{int(act_hr)}", "bpm"))
                            if act_max_hr:
                                card_data.append(("Max HR", f"{int(act_max_hr)}", "bpm"))
                            if act_cadence:
                                card_data.append(("Cadence", f"{int(act_cadence * 2)}", "spm"))
                            if act_calories:
                                card_data.append(("Calories", f"{int(act_calories)}", ""))
                            if act_elevation:
                                card_data.append(("Elevation", f"{int(act_elevation)}", "m"))
                            if act_aero_te:
                                card_data.append(("Aerobic TE", f"{act_aero_te:.1f}", ""))
                            if act_anaero_te:
                                card_data.append(("Anaerobic TE", f"{act_anaero_te:.1f}", ""))

                            if card_data:
                                st.markdown(_metrics_strip(card_data), unsafe_allow_html=True)

                            # ── Planned vs Actual comparison ──
                            planned_dist = props.get("estimated_distance_meters", 0)
                            planned_dur = props.get("estimated_duration_seconds", 0)
                            if planned_dist and act_dist:
                                dist_diff = ((act_dist - planned_dist) / planned_dist) * 100
                                dist_color = "#10B981" if abs(dist_diff) < 15 else "#F59E0B"
                                comp_html = f'<span style="color:{dist_color};">Dist: {dist_diff:+.0f}%</span>'
                                if planned_dur and act_dur:
                                    dur_diff = ((act_dur - planned_dur) / planned_dur) * 100
                                    dur_color = "#10B981" if abs(dur_diff) < 15 else "#F59E0B"
                                    comp_html += f' · <span style="color:{dur_color};">Duration: {dur_diff:+.0f}%</span>'
                                st.markdown(
                                    f'<div style="font-size:0.75rem;color:#8B95AD;margin-bottom:0.5rem;">vs Planned: {comp_html}</div>',
                                    unsafe_allow_html=True,
                                )

                            # ── Splits table (from detail data merged above) ──
                            splits_data = detail_data.get("splits") or {}
                            hr_zones_data = detail_data.get("hr_zones") or {}
                            laps = splits_data.get("lapDTOs") or []
                            if laps:
                                st.markdown(
                                    f'<div style="margin:0.5rem 0;">{_splits_table_html(laps)}</div>',
                                    unsafe_allow_html=True,
                                )

                            # ── HR Zones ──
                            hr_list = hr_zones_data if isinstance(hr_zones_data, list) else hr_zones_data.get("hrTimeInZones", []) if isinstance(hr_zones_data, dict) else []
                            if hr_list and any(zd.get("secsInZone", 0) > 0 for zd in hr_list):
                                st.markdown(
                                    f'<div style="margin:0.5rem 0;">{_hr_zone_bars_html(hr_list)}</div>',
                                    unsafe_allow_html=True,
                                )

                            # ── AI Analysis ──
                            analysis = props.get("completion_analysis", "")
                            if analysis:
                                st.markdown(
                                    f'<div class="pf-card" style="margin-top:0.5rem;border:1px solid rgba(16,185,129,0.15);">'
                                    f'<div style="color:#10B981;font-size:0.7rem;font-weight:600;margin-bottom:0.25rem;">AI ANALYSIS</div>'
                                    f'<div style="color:#E8ECF4;font-size:0.82rem;">{analysis}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                wo_name = props.get("name", "")
                                p_id = props.get("plan_id", "")
                                if st.button("Analyze with AI", key=f"analyze_{ev_date}_{wo_name}", use_container_width=True):
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
                                                    f'<div class="pf-card" style="border:1px solid rgba(16,185,129,0.15);">'
                                                    f'<div style="color:#10B981;font-size:0.7rem;font-weight:600;margin-bottom:0.25rem;">AI ANALYSIS</div>'
                                                    f'<div style="color:#E8ECF4;font-size:0.82rem;">{result.get("analysis", "")}</div>'
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

                            # ── Send to Strava button (completed planned workouts) ──
                            _plan_act_id = props.get("matched_activity_id")
                            if _plan_act_id:
                                _strava_prefs = st.session_state.get("_strava_conn")
                                if _strava_prefs is None:
                                    try:
                                        _sc = requests.get(f"{API_BASE}/strava/status", headers=_auth_headers(), timeout=5)
                                        _strava_prefs = _sc.json() if _sc.status_code == 200 else {"connected": False}
                                    except Exception:
                                        _strava_prefs = {"connected": False}
                                    st.session_state["_strava_conn"] = _strava_prefs

                                if _strava_prefs.get("connected"):
                                    _already_sent = st.session_state.get(f"strava_sent_{_plan_act_id}", False)
                                    if _already_sent:
                                        st.markdown(
                                            '<div style="color:#FC4C02;font-size:0.85rem;padding:0.4rem 0;">'
                                            '✓ Sent to Strava</div>',
                                            unsafe_allow_html=True,
                                        )
                                    elif st.button("Send to Strava", key=f"strava_push_plan_{_plan_act_id}", use_container_width=True):
                                        with st.spinner("Sending to Strava..."):
                                            try:
                                                _sr = requests.post(
                                                    f"{API_BASE}/strava/push/{_plan_act_id}",
                                                    headers=_auth_headers(),
                                                    timeout=60,
                                                )
                                                if _sr.status_code == 200:
                                                    _sdata = _sr.json()
                                                    st.session_state[f"strava_sent_{_plan_act_id}"] = True
                                                    if _sdata.get("duplicate"):
                                                        st.info("Activity already exists on Strava (auto-synced from Garmin)")
                                                    elif _sdata.get("updated"):
                                                        st.success("Activity enhanced on Strava with PaceForge data!")
                                                        st.markdown(
                                                            f'<a href="{_sdata.get("url", "")}" target="_blank" '
                                                            f'style="color:#FC4C02;">View on Strava</a>',
                                                            unsafe_allow_html=True,
                                                        )
                                                    else:
                                                        st.success("Activity posted to Strava!")
                                                        st.markdown(
                                                            f'<a href="{_sdata.get("url", "")}" target="_blank" '
                                                            f'style="color:#FC4C02;">View on Strava</a>',
                                                            unsafe_allow_html=True,
                                                        )
                                                elif _sr.status_code == 409:
                                                    st.session_state[f"strava_sent_{_plan_act_id}"] = True
                                                    st.info("Already sent to Strava")
                                                else:
                                                    st.error(f"Strava push failed: {_sr.text}")
                                            except Exception as _se:
                                                st.error(f"Strava push failed: {_se}")

                            # ── User Feedback Section ──
                            st.markdown("---")
                            wo_name = props.get("name", "")
                            p_id = props.get("plan_id", "")
                            existing_rpe = props.get("user_rpe")
                            existing_notes = props.get("user_notes", "")

                            st.markdown('<div style="color:#8B95AD;font-size:0.75rem;margin-bottom:0.25rem;">How did it feel?</div>', unsafe_allow_html=True)
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

                            if st.button("Save & Re-analyze", key=f"feedback_{ev_date}_{wo_name}", use_container_width=True):
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
                                                f'<div class="pf-card" style="border:1px solid rgba(16,185,129,0.15);">'
                                                f'<div style="color:#10B981;font-size:0.7rem;font-weight:600;margin-bottom:0.25rem;">UPDATED AI ANALYSIS</div>'
                                                f'<div style="color:#E8ECF4;font-size:0.82rem;">{result.get("analysis", "")}</div>'
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
                                st.markdown('<div style="color:#8B95AD;font-size:0.75rem;margin-bottom:0.25rem;">Match Garmin Activity</div>', unsafe_allow_html=True)
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
                                if st.button("Match & Complete", key=f"match_{ev_date}_{wo_name}", use_container_width=True):
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
                            if st.button("Delete Workout", key=f"del_{ev_date}_{props.get('name','')}", use_container_width=True):
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
                    '<div style="font-weight:700;font-size:1rem;color:#10B981;margin-bottom:0.5rem;">AI Plan Review</div>',
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

    # Lazy-load HYROX data on first tab visit
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
                f'<div style="font-size:1.2rem;font-weight:700;color:#F59E0B;margin-bottom:0.5rem;">'
                f'HYROX Results — {hx_data.get("search_name", "")}'
                f'<span style="color:#8B95AD;font-size:0.85rem;margin-left:12px;">'
                f'{len(hx_data["results"])} race(s)</span></div>',
                unsafe_allow_html=True,
            )
        with hdr_col3:
            if st.button("New Search", key="hyrox_clear_top_btn"):
                requests.delete(f"{API_BASE}/hyrox/results", headers=_auth_headers(), timeout=10)
                st.session_state.hyrox_data = None
                st.session_state.hyrox_preview = None
                st.session_state.hyrox_search_params = {}
                st.rerun()
        with hdr_col2:
            if st.button("Refresh Results", key="hyrox_refresh_btn"):
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
            '<div style="font-size:1.2rem;font-weight:700;color:#F59E0B;margin-bottom:0.5rem;">'
            'HYROX Race Results</div>'
            '<p style="color:#8B95AD;margin-bottom:1rem;">Search for your HYROX race results by name. '
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
                submitted = st.form_submit_button("Search HYROX Results", use_container_width=True)
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
                f'Found {len(preview)} race(s) matching <span style="color:#F59E0B;">{display_name}</span>. '
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
                    confirmed = st.form_submit_button("Import Selected Races", use_container_width=True)
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

        # ── Fetch analysis for selected race (cached per index) ──
        _hyrox_cache_key = f"hyrox_analysis_{selected_idx}"
        if _hyrox_cache_key not in st.session_state:
            try:
                r = requests.get(
                    f"{API_BASE}/hyrox/analyze/{selected_idx}",
                    headers=_auth_headers(), timeout=15,
                )
                st.session_state[_hyrox_cache_key] = r.json() if r.status_code == 200 else None
            except Exception:
                st.session_state[_hyrox_cache_key] = None
        analysis_data = st.session_state[_hyrox_cache_key]

        if analysis_data:
            ana = analysis_data["analysis"]
            prios = analysis_data["priorities"]

            # ══════════════════════════════════════════
            # RACE SUMMARY CARDS
            # ══════════════════════════════════════════
            st.markdown(_metrics_strip([
                ("Total Time", ana["total_time_display"], ""),
                ("Running", ana["total_running_display"], f'{ana["running_pct"]}%'),
                ("Stations", ana["total_stations_display"], f'{ana["station_pct"]}%'),
                ("Roxzone", ana["roxzone_display"], f'{ana["roxzone_pct"]}%'),
                ("Avg Run Pace", ana["avg_run_pace_display"], ""),
            ]), unsafe_allow_html=True)

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
                        wf_colors.append("#0EA5E9")
                    else:
                        wf_colors.append("#F59E0B")

                fig_wf = go.Figure()
                fig_wf.add_trace(go.Bar(
                    x=wf_labels,
                    y=wf_times,
                    marker_color=wf_colors,
                    text=[s["athlete_display"] for s in split_ana],
                    textposition="outside",
                    textfont=dict(color="#A0A8BE", size=9),
                    hovertemplate="%{x}: %{text}<extra></extra>",
                ))
                fig_wf.update_layout(**_pf_layout(
                    title="Race Segment Breakdown",
                    yaxis_title="Time (minutes)",
                    margin=dict(l=40, r=20, t=40, b=80), height=350,
                    xaxis=dict(gridcolor="rgba(148,163,194,0.06)", tickangle=-45, zeroline=False),
                    yaxis=dict(gridcolor="rgba(148,163,194,0.08)", zeroline=False),
                ))
                st.plotly_chart(fig_wf, use_container_width=True, key="hyrox_waterfall")

            # ══════════════════════════════════════════
            # RUNNING ANALYSIS — 8-bar splits + fade
            # ══════════════════════════════════════════
            st.markdown("")
            run_splits = ana.get("run_splits", [])
            if run_splits and any(s["seconds"] for s in run_splits):
                fade = ana["fade_pct"]
                running_class = ana["running_class"]
                class_colors = {"Strong Compromised Runner": "#10B981", "Moderate Drop-off": "#F59E0B", "Severe Fade": "#F43F5E"}
                cls_c = class_colors.get(running_class, "#8B95AD")

                st.markdown(
                    f'<div style="display:flex;gap:12px;align-items:center;margin-bottom:8px;">'
                    f'<span style="background:{cls_c}22;color:{cls_c};padding:4px 14px;border-radius:12px;'
                    f'font-size:0.85rem;font-weight:600;">{running_class}</span>'
                    f'<span style="color:#8B95AD;font-size:0.85rem;">Pace fade: {fade:.1f}%</span>'
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
                    textfont=dict(color="#A0A8BE", size=11),
                    hovertemplate="%{x}: %{text}/km<extra></extra>",
                ))
                fig_runs.update_layout(**_pf_layout(
                    title="Running Splits (8 x 1km)",
                    yaxis_title="Pace (min/km)", yaxis_autorange="reversed",
                    margin=dict(l=50, r=20, t=40, b=40), height=300,
                ))
                st.plotly_chart(fig_runs, use_container_width=True, key="hyrox_run_splits")

            # ══════════════════════════════════════════
            # STATION BENCHMARKS — vs field + top 3
            # ══════════════════════════════════════════
            st.markdown("")
            station_splits = [s for s in split_ana if not s["name"].startswith("Running") and s["name"] != "Roxzone_Time"]
            if station_splits:
                st.markdown(
                    '<div style="font-weight:600;color:#8B95AD;font-size:0.85rem;margin-bottom:6px;">'
                    'Station Performance vs Benchmarks</div>',
                    unsafe_allow_html=True,
                )
                bench_html = (
                    '<div style="background:#161821;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #252A35;">'
                    '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.78rem;">Station</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Your Time</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Field Avg</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Top 3 Avg</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">vs Field</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">vs Top 3</th>'
                    '</tr>'
                )
                for s in station_splits:
                    gap_f = s["gap_vs_field"]
                    gap_t = s["gap_vs_top3"]
                    f_color = "#10B981" if gap_f < 0 else "#F43F5E"
                    t_color = "#10B981" if gap_t is not None and gap_t < 0 else "#F43F5E" if gap_t is not None else "#8B95AD"
                    f_text = f'{gap_f:+.0f}s'
                    t_text = f'{gap_t:+.0f}s' if gap_t is not None else "—"
                    bench_html += (
                        f'<tr style="border-bottom:1px solid #252A3522;">'
                        f'<td style="padding:8px;color:#E8ECF4;font-weight:500;">{s["display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FBBF24;font-weight:600;">{s["athlete_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#A0A8BE;">{s["field_avg_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#A0A8BE;">{s["top3_avg_display"]}</td>'
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
                    '<div style="font-weight:600;color:#F43F5E;font-size:0.85rem;margin-bottom:6px;">'
                    'Training Priorities (Biggest Improvement Potential)</div>',
                    unsafe_allow_html=True,
                )
                # Show top 8 priorities
                top_prios = prios[:8]
                prio_html = (
                    '<div style="background:#161821;border-radius:10px;padding:12px 16px;">'
                    '<table style="width:100%;border-collapse:collapse;">'
                    '<tr style="border-bottom:1px solid #252A35;">'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">#</th>'
                    '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.78rem;">Segment</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Your Time</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Top 3 Avg</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Gap</th>'
                    '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Score</th>'
                    '</tr>'
                )
                priority_colors = ["#F43F5E", "#F43F5E", "#F43F5E", "#F59E0B", "#F59E0B", "#FBBF24", "#FBBF24", "#8B95AD"]
                for i, p in enumerate(top_prios):
                    pc = priority_colors[i] if i < len(priority_colors) else "#8B95AD"
                    t_icon = "R" if p["is_running"] else "S"
                    prio_html += (
                        f'<tr style="border-bottom:1px solid #252A3522;">'
                        f'<td style="padding:8px;text-align:center;color:{pc};font-weight:700;">#{p["rank"]}</td>'
                        f'<td style="padding:8px;color:#E8ECF4;font-weight:500;">{t_icon} {p["display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#FBBF24;">{p["athlete_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#A0A8BE;">{p["top3_avg_display"]}</td>'
                        f'<td style="padding:8px;text-align:center;color:#F43F5E;font-weight:600;">+{p["gap_seconds"]:.0f}s</td>'
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
                    '<div style="font-weight:600;color:#8B5CF6;font-size:0.85rem;margin-bottom:6px;">'
                    'AI Improvement Plan</div>'
                    '<p style="color:#8B95AD;font-size:0.8rem;margin-bottom:8px;">'
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
                                f'<div style="background:#161821;border:1px solid #8B5CF644;border-radius:10px;'
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
                '<div style="font-weight:600;color:#8B95AD;font-size:0.85rem;margin-bottom:6px;">'
                'Race History</div>',
                unsafe_allow_html=True,
            )
            try:
                if "hyrox_progression" not in st.session_state:
                    rp = requests.get(f"{API_BASE}/hyrox/progression", headers=_auth_headers(), timeout=15)
                    st.session_state.hyrox_progression = rp.json() if rp.status_code == 200 else None
                prog = st.session_state.hyrox_progression
                if prog:
                    races_data = prog.get("races", [])

                    if races_data:
                        # Race summary table
                        hist_html = (
                            '<div style="background:#161821;border-radius:10px;padding:12px 16px;margin-bottom:1rem;">'
                            '<table style="width:100%;border-collapse:collapse;">'
                            '<tr style="border-bottom:1px solid #252A35;">'
                            '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">#</th>'
                            '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.78rem;">Event</th>'
                            '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Division</th>'
                            '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Total Time</th>'
                            '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Rank</th>'
                            '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Fade %</th>'
                            '</tr>'
                        )
                        for rd in races_data:
                            fade_c = "#10B981" if rd["fade_pct"] < 8 else "#F59E0B" if rd["fade_pct"] < 15 else "#F43F5E"
                            event_label = rd.get("event_date") or rd["city"]
                            hist_html += (
                                f'<tr style="border-bottom:1px solid #252A3522;">'
                                f'<td style="padding:8px;text-align:center;color:#8B95AD;">{rd["index"]}</td>'
                                f'<td style="padding:8px;color:#E8ECF4;font-weight:500;">{event_label}</td>'
                                f'<td style="padding:8px;text-align:center;color:#A0A8BE;">{rd["division"]}</td>'
                                f'<td style="padding:8px;text-align:center;color:#FBBF24;font-weight:600;">{rd["total_display"]}</td>'
                                f'<td style="padding:8px;text-align:center;color:#A0A8BE;">{rd["rank"]}</td>'
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
                                line=dict(color="#F59E0B", width=3),
                                marker=dict(size=10, color="#F59E0B"),
                                hovertemplate="%{x}<br>%{y:.1f} min<extra></extra>",
                            ))
                            improving = prog.get("improving", False)
                            trend_title = "Total Time Trend"
                            if improving:
                                trend_title += " Improving!"
                            fig_trend.update_layout(**_pf_layout(
                                title=trend_title,
                                yaxis_title="Total Time (min)", yaxis_autorange="reversed",
                                margin=dict(l=50, r=20, t=40, b=50), height=300,
                                xaxis=dict(gridcolor="rgba(148,163,194,0.06)", tickangle=-30, zeroline=False),
                            ))
                            st.plotly_chart(fig_trend, use_container_width=True, key="hyrox_trend")

                        # Best race highlight
                        best = prog.get("best_race")
                        if best:
                            best_event = best.get("event_date") or best.get("city", "")
                            st.markdown(
                                f'<div style="background:#0D2818;border:1px solid #10B981;border-radius:8px;'
                                f'padding:10px 16px;margin-top:8px;">'
                                f'<span style="color:#10B981;font-weight:600;">Personal Best:</span> '
                                f'<span style="color:#E8ECF4;">{best["total_display"]}</span> '
                                f'<span style="color:#8B95AD;">at {best_event}</span>'
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
                                '<div style="font-weight:600;color:#8B95AD;font-size:0.85rem;margin-bottom:6px;">'
                                'Station Comparison Across Races</div>',
                                unsafe_allow_html=True,
                            )

                            # Build comparison table
                            event_labels = [rd.get("event_date") or rd["city"] for rd in races_data]
                            cmp_html = (
                                '<div style="background:#161821;border-radius:10px;padding:12px 16px;overflow-x:auto;">'
                                '<table style="width:100%;border-collapse:collapse;">'
                                '<tr style="border-bottom:1px solid #252A35;">'
                                '<th style="text-align:left;padding:8px;color:#8B95AD;font-size:0.78rem;">Segment</th>'
                            )
                            for ev in event_labels:
                                cmp_html += f'<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">{ev}</th>'
                            cmp_html += '<th style="text-align:center;padding:8px;color:#8B95AD;font-size:0.78rem;">Change</th>'
                            cmp_html += '</tr>'

                            for sc in station_cmp:
                                icon = "R" if sc["is_running"] else "S"
                                cmp_html += f'<tr style="border-bottom:1px solid #252A3522;">'
                                cmp_html += f'<td style="padding:8px;color:#E8ECF4;font-weight:500;">{icon} {sc["display"]}</td>'

                                # Per-race times — highlight best in green
                                race_times = sc["times"]
                                valid_secs = [t["seconds"] for t in race_times if t["seconds"]]
                                best_sec = min(valid_secs) if valid_secs else None

                                for t in race_times:
                                    if t["seconds"] is None:
                                        cmp_html += '<td style="padding:8px;text-align:center;color:#8B95AD;">—</td>'
                                    elif t["seconds"] == best_sec:
                                        cmp_html += f'<td style="padding:8px;text-align:center;color:#10B981;font-weight:600;">{t["display"]}</td>'
                                    else:
                                        cmp_html += f'<td style="padding:8px;text-align:center;color:#A0A8BE;">{t["display"]}</td>'

                                # Improvement column
                                imp = sc.get("improvement_seconds")
                                if imp is not None and abs(imp) >= 1:
                                    if imp > 0:
                                        imp_c = "#10B981"
                                        imp_text = f"-{int(imp)}s"
                                    else:
                                        imp_c = "#F43F5E"
                                        imp_text = f"+{int(abs(imp))}s"
                                    cmp_html += f'<td style="padding:8px;text-align:center;color:{imp_c};font-weight:600;">{imp_text}</td>'
                                else:
                                    cmp_html += '<td style="padding:8px;text-align:center;color:#8B95AD;">—</td>'
                                cmp_html += '</tr>'

                            cmp_html += '</table></div>'
                            st.markdown(cmp_html, unsafe_allow_html=True)

                            # Station comparison bar chart — stations only (not runs)
                            station_only = [sc for sc in station_cmp if not sc["is_running"] and sc["name"] != "Roxzone_Time"]
                            if station_only:
                                st.markdown("")
                                fig_cmp = go.Figure()
                                bar_colors = ["#F59E0B", "#0EA5E9", "#10B981", "#8B5CF6", "#F43F5E", "#FBBF24"]
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
                                        textfont=dict(color="#A0A8BE", size=9),
                                    ))
                                fig_cmp.update_layout(**_pf_layout(
                                    title="Station Times: Race-by-Race Comparison",
                                    yaxis_title="Time (min)",
                                    barmode="group",
                                    margin=dict(l=50, r=20, t=40, b=80), height=380,
                                    xaxis=dict(gridcolor="rgba(148,163,194,0.06)", tickangle=-30, zeroline=False),
                                    yaxis=dict(gridcolor="rgba(148,163,194,0.08)", zeroline=False),
                                    legend=dict(font=dict(color="#8B95AD")),
                                ))
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
                    st.session_state.analytics = analytics
            except Exception:
                pass

        hx_pred = (analytics or {}).get("hyrox", {})
        sus_pace = hx_pred.get("sustainable_1km_pace")
        pred_splits = hx_pred.get("race_1km_splits", [])
        if sus_pace and pred_splits:
            st.markdown("")
            st.markdown(
                '<div style="font-size:1.05rem;font-weight:700;color:#F59E0B;margin-bottom:0.5rem;">'
                'Running Performance Predictions</div>'
                '<div style="font-size:0.8rem;color:#8B95AD;margin-bottom:0.8rem;">'
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
        if st.button("Clear saved results and search again", key="hyrox_clear_btn"):
            requests.delete(f"{API_BASE}/hyrox/results", headers=_auth_headers(), timeout=10)
            st.session_state.hyrox_data = None
            st.session_state.hyrox_preview = None
            st.session_state.hyrox_search_params = {}
            st.rerun()


# ── Tab 5: AI Coach ──────────────────────────────────────────────────

with tab_coach:
    st.markdown('<div class="pf-section-header">AI Running Coach</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#8B95AD;margin-bottom:1rem;">Ask questions about your training and get personalized advice.</p>',
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

    sub_account, sub_friends, sub_connections = st.tabs(["Account", "Friends", "Connections"])

    # ── Sub-tab: Account Information ──
    with sub_account:
        _, col_form, _ = st.columns([1, 2, 1])
        with col_form:
            st.markdown('<div class="pf-section-header">Account Information</div>', unsafe_allow_html=True)

            with st.form("up_profile_form"):
                new_name = st.text_input("Name", value=st.session_state.user_name or "", key="up_name")
                new_email = st.text_input("Email", value=st.session_state.user_email or "", key="up_email")
                st.markdown(
                    '<div style="margin-top:0.5rem;font-size:0.8rem;color:#8B95AD;">'
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

    # ── Sub-tab: Friends ──
    with sub_friends:
        st.markdown('<div class="pf-section-header">Friends</div>', unsafe_allow_html=True)

        # Load friends data (lazy on first visit)
        if "friends_data" not in st.session_state:
            try:
                friends_r = requests.get(f"{API_BASE}/friends", headers=_auth_headers(), timeout=10)
                st.session_state.friends_data = friends_r.json() if friends_r.status_code == 200 else {}
            except Exception:
                st.session_state.friends_data = {}
        friends_data = st.session_state.friends_data

        friends_list = friends_data.get("friends", [])
        pending_reqs = friends_data.get("pending", [])
        sent_reqs = friends_data.get("sent", [])

        # Pending requests (incoming) — show first so they're prominent
        if pending_reqs:
            st.markdown(f"**Pending Requests ({len(pending_reqs)})**")
            for pr in pending_reqs:
                col_info, col_accept, col_reject = st.columns([3, 1, 1])
                with col_info:
                    st.markdown(
                        f'<div style="padding:0.3rem 0;color:#E8ECF4;">{pr["name"]}'
                        f'<span style="color:#8B95AD;font-size:0.8rem;margin-left:0.4rem;">{pr["email"]}</span></div>',
                        unsafe_allow_html=True,
                    )
                with col_accept:
                    if st.button("✓", key=f"accept_{pr['friendship_id']}", use_container_width=True):
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
                    if st.button("✗", key=f"reject_{pr['friendship_id']}", use_container_width=True):
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
                        f'<div style="width:32px;height:32px;border-radius:50%;background:#10B98133;'
                        f'display:flex;align-items:center;justify-content:center;color:#10B981;'
                        f'font-weight:700;font-size:0.8rem;">{fr_initials}</div>'
                        f'<div><span style="color:#E8ECF4;font-weight:500;">{fr["name"]}</span>'
                        f'<span style="color:#8B95AD;font-size:0.75rem;margin-left:0.3rem;">since {since}</span>'
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

        # ── All Users Directory ──
        st.markdown("---")
        st.markdown("**People on PaceForge**")
        if "all_approved_users" not in st.session_state:
            try:
                _au_r = requests.get(f"{API_BASE}/users/approved", headers=_auth_headers(), timeout=10)
                st.session_state.all_approved_users = _au_r.json() if _au_r.status_code == 200 else []
            except Exception:
                st.session_state.all_approved_users = []
        _all_users = st.session_state.all_approved_users

        if _all_users:
            _existing_friend_ids = {f["id"] for f in friends_list}
            _pending_sent_ids = {r["id"] for r in sent_reqs}
            _pending_recv_ids = {r["id"] for r in pending_reqs}
            for _au in _all_users:
                _au_col_info, _au_col_action = st.columns([3, 1])
                with _au_col_info:
                    _au_init = "".join(w[0].upper() for w in _au["name"].split()[:2]) if _au.get("name") else "?"
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:0.6rem;padding:0.35rem 0;">'
                        f'<div style="width:30px;height:30px;border-radius:50%;background:#10B98122;'
                        f'display:flex;align-items:center;justify-content:center;color:#10B981;'
                        f'font-weight:700;font-size:0.75rem;">{_au_init}</div>'
                        f'<div><span style="color:#E8ECF4;font-weight:500;">{_au["name"]}</span>'
                        f'<span style="color:#8B95AD;font-size:0.8rem;margin-left:0.4rem;">{_au["email"]}</span>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                with _au_col_action:
                    if _au["id"] in _existing_friend_ids:
                        st.markdown(
                            '<span style="color:#10B981;font-size:0.82rem;">Friends</span>',
                            unsafe_allow_html=True,
                        )
                    elif _au["id"] in _pending_sent_ids:
                        st.markdown(
                            '<span style="color:#F59E0B;font-size:0.82rem;">Pending</span>',
                            unsafe_allow_html=True,
                        )
                    elif _au["id"] in _pending_recv_ids:
                        st.markdown(
                            '<span style="color:#0EA5E9;font-size:0.82rem;">Accept above</span>',
                            unsafe_allow_html=True,
                        )
                    else:
                        if st.button("Add", key=f"add_user_{_au['id']}", use_container_width=True):
                            try:
                                requests.post(
                                    f"{API_BASE}/friends/request",
                                    json={"recipient_id": _au["id"]},
                                    headers=_auth_headers(), timeout=10,
                                )
                                st.session_state.pop("friends_data", None)
                                st.session_state.pop("all_approved_users", None)
                                st.rerun()
                            except requests.ConnectionError:
                                st.error("Cannot reach API")
        else:
            st.markdown(
                '<div style="text-align:center;padding:1.5rem;color:#8B95AD;">'
                "No other users on the platform yet.</div>",
                unsafe_allow_html=True,
            )

    # ── Sub-tab: Connections ──
    with sub_connections:
        _, col_conn, _ = st.columns([1, 2, 1])
        with col_conn:
            st.markdown('<div class="pf-section-header">Garmin Connect</div>', unsafe_allow_html=True)

            # ── Activity type sync preferences ──
            if st.session_state.garmin_logged_in:
                if "sync_prefs" not in st.session_state:
                    try:
                        _pr = requests.get(f"{API_BASE}/preferences", headers=_auth_headers(), timeout=10)
                        st.session_state.sync_prefs = _pr.json() if _pr.status_code == 200 else {"sync_activity_types": ["running", "fitness_equipment"]}
                    except Exception:
                        st.session_state.sync_prefs = {"sync_activity_types": ["running", "fitness_equipment"]}
                _cur_types = st.session_state.sync_prefs.get("sync_activity_types", ["running"])

                st.markdown(
                    '<div style="margin-bottom:0.25rem;color:#8B95AD;font-size:0.8rem;font-weight:600;">Sync Activity Types</div>',
                    unsafe_allow_html=True,
                )
                _sync_running = st.checkbox("Running", value="running" in _cur_types, key="pref_sync_running")
                _sync_cardio = st.checkbox("Cardio / HIIT", value=any(t in _cur_types for t in ("fitness_equipment", "fitness", "cardio")), key="pref_sync_cardio")

                _new_types = []
                if _sync_running:
                    _new_types.append("running")
                if _sync_cardio:
                    _new_types.append("fitness_equipment")
                if not _new_types:
                    _new_types = ["running"]

                if set(_new_types) != set(_cur_types):
                    try:
                        _new_prefs = {"sync_activity_types": _new_types}
                        requests.put(
                            f"{API_BASE}/preferences",
                            json=_new_prefs,
                            headers=_auth_headers(), timeout=10,
                        )
                        st.session_state.sync_prefs = _new_prefs
                        # Auto re-sync activities with updated preferences
                        with st.spinner("Re-syncing activities with new preferences..."):
                            _ar = requests.get(
                                f"{API_BASE}/activities?days=240&sync=true",
                                headers=_auth_headers(), timeout=60,
                            )
                            if _ar.status_code == 200:
                                st.session_state["garmin_activities"] = _ar.json()
                        st.rerun()
                    except Exception:
                        st.error("Failed to save preferences")

                st.markdown(
                    '<div style="color:#8B95AD;font-size:0.7rem;margin-bottom:1rem;">'
                    "Cardio/HIIT includes elliptical, rowing, gym sessions, and similar activities.</div>",
                    unsafe_allow_html=True,
                )

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
                    '<div style="background:#10B98122;border:1px solid #10B98144;'
                    "border-radius:12px;padding:1.5rem;text-align:center;margin-bottom:1rem;\">"
                    '<div style="font-size:2rem;margin-bottom:0.5rem;">⌚</div>'
                    '<div style="color:#10B981;font-weight:600;font-size:1.1rem;">Connected</div>'
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

            # ── Future Connectors ──
            st.markdown("---")
            st.markdown('<div class="pf-section-header">Other Services</div>', unsafe_allow_html=True)

            # ── Strava Connection ──
            _strava_status = None
            try:
                _sr = requests.get(f"{API_BASE}/strava/status", headers=_auth_headers(), timeout=10)
                if _sr.status_code == 200:
                    _strava_status = _sr.json()
            except Exception:
                pass

            if _strava_status and _strava_status.get("connected"):
                _ath_name = _strava_status.get("athlete_name", "Connected")
                st.markdown(
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'padding:0.75rem 1rem;background:#1A1D2B;border:1px solid #FC4C02;'
                    f'border-radius:10px;margin-bottom:0.5rem;">'
                    f'<div><span style="color:#FC4C02;font-weight:600;">Strava</span>'
                    f'<span style="color:#8B95AD;font-size:0.8rem;margin-left:0.5rem;">{_ath_name}</span></div>'
                    f'<span style="color:#10B981;font-size:0.8rem;">Connected</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Disconnect Strava", key="strava_disconnect", use_container_width=True):
                    try:
                        requests.delete(f"{API_BASE}/strava/disconnect", headers=_auth_headers(), timeout=10)
                        st.rerun()
                    except Exception as _se:
                        st.error(f"Failed to disconnect: {_se}")
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;justify-content:space-between;'
                    'padding:0.75rem 1rem;background:#1A1D2B;border:1px solid #2A2D3B;'
                    'border-radius:10px;margin-bottom:0.5rem;">'
                    '<span style="color:#E8ECF4;font-weight:500;">Strava</span>'
                    '<span style="color:#8B95AD;font-size:0.8rem;">Not connected</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Connect Strava", key="strava_connect", use_container_width=True):
                    try:
                        _ar = requests.get(f"{API_BASE}/strava/auth-url", headers=_auth_headers(), timeout=10)
                        if _ar.status_code == 200:
                            _auth_url = _ar.json().get("url", "")
                            if _auth_url:
                                st.markdown(
                                    f'<a href="{_auth_url}" target="_blank" style="color:#FC4C02;font-weight:600;">'
                                    f'Click here to authorize on Strava</a>',
                                    unsafe_allow_html=True,
                                )
                        elif _ar.status_code == 503:
                            st.warning("Strava integration is not configured on the server.")
                        else:
                            st.error(f"Failed to get auth URL: {_ar.text}")
                    except Exception as _se:
                        st.error(f"Failed: {_se}")

            # ── Other services (coming soon) ──
            for svc in ["Polar", "COROS"]:
                st.markdown(
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'padding:0.75rem 1rem;background:#1A1D2B;border:1px solid #2A2D3B;'
                    f'border-radius:10px;margin-bottom:0.5rem;">'
                    f'<span style="color:#E8ECF4;font-weight:500;">{svc}</span>'
                    f'<span style="color:#8B95AD;font-size:0.8rem;">Coming soon</span>'
                    f'</div>',
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
                for k in list(st.session_state.keys()):
                    if k.startswith("admin_users_"):
                        del st.session_state[k]
                st.rerun()

        query = f"?status={status_filter}" if status_filter != "all" else ""
        _admin_cache_key = f"admin_users_{status_filter}"
        if _admin_cache_key not in st.session_state:
            try:
                r = requests.get(
                    f"{API_BASE}/admin/users{query}",
                    headers=_auth_headers(),
                    timeout=15,
                )
                if r.status_code == 200:
                    st.session_state[_admin_cache_key] = r.json()
                else:
                    st.session_state[_admin_cache_key] = []
                    st.error(f"Failed to load users: {_error_detail(r)}")
            except (requests.ConnectionError, requests.ReadTimeout):
                st.session_state[_admin_cache_key] = []
                st.error("Cannot reach API")
        users = st.session_state[_admin_cache_key]

        if not users:
            st.markdown(
                '<p style="color:#8B95AD;text-align:center;margin:2rem 0;">No users found.</p>',
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
                            <div style="color:#8B95AD;font-size:0.82rem;">
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
