"""PaceForge — Streamlit Dashboard."""

from __future__ import annotations

import json
from datetime import date, timedelta

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="PaceForge", page_icon="🏃", layout="wide")
st.title("🏃 PaceForge — Running Plan Generator")


# ── Session state ────────────────────────────────────────────────────

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "mfa_required" not in st.session_state:
    st.session_state.mfa_required = False
if "profile" not in st.session_state:
    st.session_state.profile = None
if "plan" not in st.session_state:
    st.session_state.plan = None


# ── Sidebar: Auth ────────────────────────────────────────────────────

with st.sidebar:
    st.header("Garmin Connect")

    if not st.session_state.logged_in:
        if not st.session_state.mfa_required:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login", type="primary"):
                try:
                    with st.spinner("Authenticating with Garmin (may take up to 90s)..."):
                        r = requests.post(
                            f"{API_BASE}/auth/login",
                            json={"email": email, "password": password},
                            timeout=120,
                        )
                    data = r.json()
                    if r.status_code == 200 and data.get("status") == "mfa_required":
                        st.session_state.mfa_required = True
                        st.info("Check your email for the verification code.")
                        st.rerun()
                    elif r.status_code == 200:
                        st.session_state.logged_in = True
                        st.success("Connected to Garmin!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {data.get('detail', r.text)}")
                except requests.ReadTimeout:
                    st.error("Login timed out. Garmin may be rate-limiting. Wait a few minutes and retry.")
                except requests.ConnectionError:
                    st.error("Cannot reach PaceForge API. Is the server running?")
        else:
            st.info("Garmin sent a verification code to your email.")
            mfa_code = st.text_input("MFA Code", placeholder="123456")
            if st.button("Submit Code", type="primary"):
                try:
                    r = requests.post(
                        f"{API_BASE}/auth/mfa",
                        json={"code": mfa_code},
                        timeout=30,
                    )
                    if r.status_code == 200:
                        st.session_state.mfa_required = False
                        st.session_state.logged_in = True
                        st.success("MFA verified — connected to Garmin!")
                        st.rerun()
                    else:
                        st.error(f"MFA failed: {r.json().get('detail', r.text)}")
                except requests.ConnectionError:
                    st.error("Cannot reach PaceForge API. Is the server running?")
    else:
        st.success("Connected to Garmin Connect")
        if st.button("Refresh Profile"):
            r = requests.get(f"{API_BASE}/profile", timeout=30)
            if r.status_code == 200:
                st.session_state.profile = r.json()


# ── Main content ─────────────────────────────────────────────────────

if not st.session_state.logged_in:
    st.info("Login to Garmin Connect using the sidebar to get started.")
    st.stop()


# ── Tabs ─────────────────────────────────────────────────────────────

tab_profile, tab_plan, tab_push, tab_coach = st.tabs(
    ["📊 Fitness Profile", "📅 Training Plan", "⬆️ Push to Garmin", "💬 AI Coach"]
)


# ── Tab 1: Profile ───────────────────────────────────────────────────

with tab_profile:
    if st.button("Load Fitness Profile"):
        with st.spinner("Fetching from Garmin Connect..."):
            r = requests.get(f"{API_BASE}/profile", timeout=60)
            if r.status_code == 200:
                st.session_state.profile = r.json()
            else:
                st.error("Failed to fetch profile")

    p = st.session_state.profile
    if p:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("VO2 Max", f"{p.get('vo2_max', '—')}")
        col2.metric("Resting HR", f"{p.get('resting_hr', '—')} bpm")
        col3.metric("Training Readiness", f"{p.get('training_readiness', '—')}")
        col4.metric("HRV Status", p.get("hrv_status", "—"))

        st.subheader("Race Predictions")
        preds = p.get("race_predictions", [])
        if preds:
            for pred in preds:
                secs = pred["predicted_seconds"]
                h = int(secs) // 3600
                m = (int(secs) % 3600) // 60
                s = int(secs) % 60
                time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
                st.write(f"**{pred['distance']}**: {time_str}")
        else:
            st.write("No race predictions available")

        st.subheader("Weekly Mileage")
        st.write(f"{p.get('weekly_mileage_km', '—')} km/week (last 30 days)")

        st.subheader("Recent Activities")
        acts = p.get("recent_activities", [])
        if acts:
            for a in acts[:10]:
                dist = round(a.get("distance_meters", 0) / 1000, 1)
                pace = a.get("avg_pace_sec_per_km")
                pace_str = ""
                if pace:
                    pm, ps = divmod(int(pace), 60)
                    pace_str = f" @ {pm}:{ps:02d}/km"
                st.write(f"- {a['name']}: {dist} km{pace_str}")
    else:
        st.info("Click 'Load Fitness Profile' to view your data.")


# ── Tab 2: Generate Plan ─────────────────────────────────────────────

with tab_plan:
    st.subheader("Generate a Training Plan")

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
        long_run_day = st.selectbox("Long Run Day", ["sunday", "saturday"])

    target_secs = (target_time_h * 3600 + target_time_m * 60) if (target_time_h + target_time_m) > 0 else None

    if st.button("Generate Plan", type="primary"):
        with st.spinner("Building your personalized plan..."):
            r = requests.post(
                f"{API_BASE}/plan/generate",
                json={
                    "goal_type": goal_type,
                    "target_date": str(target_date),
                    "target_time_seconds": target_secs,
                    "experience_level": experience,
                    "long_run_day": long_run_day,
                },
                timeout=30,
            )
            if r.status_code == 200:
                st.session_state.plan = r.json()
                st.success("Plan generated!")
            else:
                st.error(f"Error: {r.json().get('detail', r.text)}")

    plan = st.session_state.plan
    if plan:
        st.divider()
        st.subheader(plan["name"])

        paces = {}
        for key in ["easy_pace", "marathon_pace", "threshold_pace", "interval_pace"]:
            val = plan.get(key)
            if val:
                pm, ps = divmod(int(val), 60)
                paces[key.replace("_pace", "").title()] = f"{pm}:{ps:02d}/km"
        if paces:
            st.write("**Training Paces:** " + " | ".join(f"{k}: {v}" for k, v in paces.items()))

        for week in plan.get("weeks", []):
            focus = week.get('focus', '')
            with st.expander(
                f"Week {week['week_number']} — {week['phase']}"
                f" ({week.get('total_distance_km', 0)} km)"
                f"{' | ' + focus if focus else ''}"
            ):
                for w in week.get("workouts", []):
                    if w["workout_type"] == "rest":
                        st.write(f"🛌 **{w.get('scheduled_date', '')}** — Rest")
                    else:
                        dist = round(
                            w.get("estimated_distance_meters", 0) / 1000, 1
                        )
                        purpose = w.get("purpose", "")
                        purpose_str = f" [{purpose}]" if purpose else ""
                        st.write(
                            f"🏃 **{w.get('scheduled_date', '')}** — "
                            f"{w['name']} ({dist} km){purpose_str}"
                        )
                        if w.get("notes"):
                            st.caption(w["notes"])

        st.divider()
        if st.button("Adapt Plan (re-evaluate)"):
            with st.spinner("Adapting plan based on latest fitness..."):
                r = requests.post(
                    f"{API_BASE}/plan/adapt",
                    timeout=30,
                )
                if r.status_code == 200:
                    st.session_state.plan = r.json()
                    st.success("Plan adapted!")
                    st.rerun()
                else:
                    st.error(f"Error: {r.json().get('detail', r.text)}")


# ── Tab 3: Push to Garmin ────────────────────────────────────────────

with tab_push:
    plan = st.session_state.plan
    if not plan:
        st.info("Generate a plan first.")
    else:
        st.subheader("Push Workouts to Garmin Connect")
        st.write("Select which weeks to push to your Garmin calendar.")

        week_options = [f"Week {w['week_number']} — {w['phase']}" for w in plan.get("weeks", [])]
        selected = st.multiselect("Weeks", week_options)

        if st.button("Push Selected Weeks", type="primary"):
            week_nums = [int(s.split()[1]) for s in selected]
            with st.spinner("Pushing workouts to Garmin Connect..."):
                r = requests.post(
                    f"{API_BASE}/plan/push",
                    json={"week_numbers": week_nums},
                    timeout=120,
                )
                if r.status_code == 200:
                    data = r.json()
                    st.success(f"Pushed {data['workouts_pushed']} workouts to Garmin Connect!")
                else:
                    st.error(f"Error: {r.json().get('detail', r.text)}")


# ── Tab 4: AI Coach ──────────────────────────────────────────────────

with tab_coach:
    st.subheader("AI Running Coach")
    st.caption("Ask questions about your training, get personalized advice.")

    user_msg = st.text_area("Your question", placeholder="How should I adjust if I missed two runs this week?")
    if st.button("Ask Coach"):
        with st.spinner("Thinking..."):
            r = requests.post(
                f"{API_BASE}/coach/chat",
                json={"message": user_msg},
                timeout=30,
            )
            if r.status_code == 200:
                st.markdown(r.json()["reply"])
            else:
                st.error("Coach unavailable")
