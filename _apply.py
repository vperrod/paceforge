"""Apply all PaceForge feature changes."""
import pathlib, sys

ROOT = pathlib.Path(r"C:\Users\vipe\paceforge\src\paceforge")
OK = FAIL = 0

def _replace(content, old, new, label):
    global OK, FAIL
    if old not in content:
        print(f"  [FAIL] {label}: marker not found")
        FAIL += 1
        return content
    result = content.replace(old, new, 1)
    OK += 1
    print(f"  [OK] {label}")
    return result

def apply_models():
    print("\n=== models/profile.py ===")
    p = ROOT / "models" / "profile.py"
    c = p.read_text(encoding="utf-8")
    c = _replace(c,
        "    vo2_max_value: float | None = None\n\n\nclass UserFitnessProfile",
        "    vo2_max_value: float | None = None\n    avg_running_cadence: float | None = None\n\n\nclass UserFitnessProfile",
        "RecentActivity.avg_running_cadence")
    c = _replace(c,
        '    long_run_day: str = Field(default="sunday", description="Preferred long run day")\n\n    @property',
        '    long_run_day: str = Field(default="sunday", description="Preferred long run day")\n'
        '    start_date: date | None = Field(None, description="Optional plan start date")\n'
        '    custom_easy_pace: float | None = Field(None, description="User-provided easy pace in sec/km")\n'
        '    custom_marathon_pace: float | None = Field(None, description="User-provided marathon pace in sec/km")\n'
        '    custom_threshold_pace: float | None = Field(None, description="User-provided threshold pace in sec/km")\n'
        '\n    @property',
        "TrainingGoal custom fields")
    p.write_text(c, encoding="utf-8")

def apply_garmin():
    print("\n=== garmin/client.py ===")
    p = ROOT / "garmin" / "client.py"
    c = p.read_text(encoding="utf-8")
    c = _replace(c,
        "def get_fitness_profile(self, lookback_days: int = 30)",
        "def get_fitness_profile(self, lookback_days: int = 90)",
        "lookback 30->90")
    c = _replace(c,
        '                        vo2_max_value=act.get("vO2MaxValue"),\n                    )\n                )',
        '                        vo2_max_value=act.get("vO2MaxValue"),\n'
        '                        avg_running_cadence=act.get("averageRunningCadenceInStepsPerMinute"),\n'
        '                    )\n                )',
        "parse cadence")
    p.write_text(c, encoding="utf-8")

def apply_api():
    print("\n=== api/app.py ===")
    p = ROOT / "api" / "app.py"
    c = p.read_text(encoding="utf-8")
    c = _replace(c,
        '    long_run_day: str = "sunday"\n\n\nclass PushPlanRequest',
        '    long_run_day: str = "sunday"\n'
        '    start_date: date | None = None\n'
        '    custom_easy_pace: float | None = None\n'
        '    custom_marathon_pace: float | None = None\n'
        '    custom_threshold_pace: float | None = None\n'
        '\n\nclass PushPlanRequest',
        "GeneratePlanRequest fields")
    c = _replace(c,
        "        long_run_day=req.long_run_day,\n    )\n\n    _user_plan[uid] = generate_plan(profile, goal)",
        "        long_run_day=req.long_run_day,\n"
        "        start_date=req.start_date,\n"
        "        custom_easy_pace=req.custom_easy_pace,\n"
        "        custom_marathon_pace=req.custom_marathon_pace,\n"
        "        custom_threshold_pace=req.custom_threshold_pace,\n"
        "    )\n\n    _user_plan[uid] = generate_plan(profile, goal)",
        "TrainingGoal constructor")
    p.write_text(c, encoding="utf-8")

def apply_planner():
    print("\n=== engine/planner.py ===")
    p = ROOT / "engine" / "planner.py"
    c = p.read_text(encoding="utf-8")
    c = _replace(c,
        "    paces = _derive_paces(profile)\n\n    # 2. Load template",
        "    paces = _derive_paces(profile)\n"
        "    # Override with user-provided custom paces if given\n"
        "    if paces and (goal.custom_easy_pace or goal.custom_marathon_pace or goal.custom_threshold_pace):\n"
        "        paces = TrainingPaces(\n"
        "            vdot=paces.vdot,\n"
        "            easy_low=goal.custom_easy_pace or paces.easy_low,\n"
        "            easy_high=goal.custom_easy_pace or paces.easy_high,\n"
        "            marathon=goal.custom_marathon_pace or paces.marathon,\n"
        "            threshold=goal.custom_threshold_pace or paces.threshold,\n"
        "            interval=paces.interval,\n"
        "            repetition=paces.repetition,\n"
        "        )\n"
        "    elif not paces and (goal.custom_easy_pace or goal.custom_marathon_pace or goal.custom_threshold_pace):\n"
        "        easy = goal.custom_easy_pace or 360\n"
        "        marathon = goal.custom_marathon_pace or 300\n"
        "        threshold = goal.custom_threshold_pace or 270\n"
        "        paces = TrainingPaces(\n"
        "            vdot=0,\n"
        "            easy_low=easy,\n"
        "            easy_high=easy,\n"
        "            marathon=marathon,\n"
        "            threshold=threshold,\n"
        "            interval=threshold - 20,\n"
        "            repetition=threshold - 40,\n"
        "        )\n"
        "\n    # 2. Load template",
        "custom paces override")
    c = _replace(c,
        "    plan_start = race_date - timedelta(weeks=total_weeks)\n"
        "    plan_start = plan_start - timedelta(days=plan_start.weekday())",
        "    if goal.start_date:\n"
        "        plan_start = goal.start_date\n"
        "        plan_start = plan_start - timedelta(days=plan_start.weekday())\n"
        "        available_weeks = (race_date - plan_start).days // 7\n"
        "        total_weeks = min(total_weeks, max(available_weeks, 4))\n"
        "    else:\n"
        "        plan_start = race_date - timedelta(weeks=total_weeks)\n"
        "        plan_start = plan_start - timedelta(days=plan_start.weekday())",
        "custom start_date")
    p.write_text(c, encoding="utf-8")

def apply_dashboard():
    print("\n=== dashboard.py ===")
    p = ROOT / "dashboard.py"
    c = p.read_text(encoding="utf-8")
    c = _replace(c,
        '        target_date = st.date_input(\n'
        '            "Race Date",\n'
        '            value=date.today() + timedelta(weeks=14),\n'
        '            min_value=date.today() + timedelta(weeks=6),\n'
        '        )\n\n'
        '        col1, col2 = st.columns(2)',
        '        target_date = st.date_input(\n'
        '            "Race Date",\n'
        '            value=date.today() + timedelta(weeks=14),\n'
        '            min_value=date.today() + timedelta(weeks=6),\n'
        '        )\n'
        '        start_date = st.date_input(\n'
        '            "Plan Start Date",\n'
        '            value=date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7),\n'
        '            min_value=date.today(),\n'
        '            max_value=target_date - timedelta(weeks=4),\n'
        '            help="When to start training. Aligns to Monday automatically.",\n'
        '        )\n\n'
        '        col1, col2 = st.columns(2)',
        "start_date picker")
    c = _replace(c,
        "        target_secs = (target_time_h * 3600 + target_time_m * 60) if (target_time_h + target_time_m) > 0 else None\n"
        "        st.markdown('</div>', unsafe_allow_html=True)",
        "        target_secs = (target_time_h * 3600 + target_time_m * 60) if (target_time_h + target_time_m) > 0 else None\n"
        "\n"
        "        st.markdown('<div class=\"pf-section-header\" style=\"font-size:0.9rem;margin-top:1rem;\">'\n"
        "                    'Current Paces (optional \\u2014 leave 0 to auto-detect from Garmin)</div>',\n"
        "                    unsafe_allow_html=True)\n"
        "        pace_cols = st.columns(3)\n"
        "        with pace_cols[0]:\n"
        "            easy_min = st.number_input(\"Easy pace min/km\", 0, 10, 0, key=\"custom_easy_min\")\n"
        "            easy_sec = st.number_input(\"Easy pace sec\", 0, 59, 0, key=\"custom_easy_sec\")\n"
        "        with pace_cols[1]:\n"
        "            marathon_min = st.number_input(\"Marathon pace min/km\", 0, 10, 0, key=\"custom_marathon_min\")\n"
        "            marathon_sec = st.number_input(\"Marathon pace sec\", 0, 59, 0, key=\"custom_marathon_sec\")\n"
        "        with pace_cols[2]:\n"
        "            threshold_min = st.number_input(\"Threshold pace min/km\", 0, 10, 0, key=\"custom_threshold_min\")\n"
        "            threshold_sec = st.number_input(\"Threshold pace sec\", 0, 59, 0, key=\"custom_threshold_sec\")\n"
        "\n"
        "        custom_easy = (easy_min * 60 + easy_sec) if (easy_min + easy_sec) > 0 else None\n"
        "        custom_marathon = (marathon_min * 60 + marathon_sec) if (marathon_min + marathon_sec) > 0 else None\n"
        "        custom_threshold = (threshold_min * 60 + threshold_sec) if (threshold_min + threshold_sec) > 0 else None\n"
        "\n"
        "        st.markdown('</div>', unsafe_allow_html=True)",
        "pace override fields")
    c = _replace(c,
        '                    json={\n'
        '                        "goal_type": goal_type,\n'
        '                        "target_date": str(target_date),\n'
        '                        "target_time_seconds": target_secs,\n'
        '                        "experience_level": experience,\n'
        '                        "training_days": training_days,\n'
        '                        "long_run_day": long_run_day,\n'
        '                    },',
        '                    json={\n'
        '                        "goal_type": goal_type,\n'
        '                        "target_date": str(target_date),\n'
        '                        "target_time_seconds": target_secs,\n'
        '                        "experience_level": experience,\n'
        '                        "training_days": training_days,\n'
        '                        "long_run_day": long_run_day,\n'
        '                        "start_date": str(start_date),\n'
        '                        "custom_easy_pace": custom_easy,\n'
        '                        "custom_marathon_pace": custom_marathon,\n'
        '                        "custom_threshold_pace": custom_threshold,\n'
        '                    },',
        "JSON payload")
    old_section = (
        '            st.markdown("")\n'
        '\n'
        '            # \u2500\u2500 Recent Activities \u2500\u2500\n'
        '            st.markdown(\'<div class="pf-section-header">Recent Activities</div>\', unsafe_allow_html=True)\n'
        '            acts = p.get("recent_activities", [])\n'
        '            if acts:\n'
        '                st.markdown(\'<div class="pf-card">\', unsafe_allow_html=True)\n'
        '                for a in acts[:10]:\n'
        '                    dist = round(a.get("distance_meters", 0) / 1000, 1)\n'
        '                    pace = a.get("avg_pace_sec_per_km")\n'
        '                    pace_str = ""\n'
        '                    if pace:\n'
        '                        pm, ps = divmod(int(pace), 60)\n'
        '                        pace_str = f"{pm}:{ps:02d}/km"\n'
        '                    st.markdown(\n'
        '                        f"""<div class="pf-activity-row">\n'
        "                            <span class=\"pf-activity-name\">{a['name']}</span>\n"
        '                            <span class="pf-activity-dist">{dist} km</span>\n'
        '                            <span class="pf-activity-pace">{pace_str}</span>\n'
        '                        </div>""",\n'
        '                        unsafe_allow_html=True,\n'
        '                    )\n'
        "                st.markdown('</div>', unsafe_allow_html=True)"
    )
    new_section = (
        '            st.markdown("")\n'
        '\n'
        '            # \u2500\u2500 Progress Trends \u2500\u2500\n'
        '            acts = p.get("recent_activities", [])\n'
        '            if acts and len(acts) >= 2:\n'
        '                st.markdown(\'<div class="pf-section-header">Progress Trends</div>\', unsafe_allow_html=True)\n'
        '                import plotly.graph_objects as go\n'
        '\n'
        '                sorted_acts = sorted(acts, key=lambda a: a.get("start_time", ""))\n'
        '                dates = [a.get("start_time", "")[:10] for a in sorted_acts]\n'
        '\n'
        '                chart_layout = dict(\n'
        '                    paper_bgcolor="rgba(0,0,0,0)",\n'
        '                    plot_bgcolor="rgba(0,0,0,0)",\n'
        '                    font=dict(color="#C9CDD4", size=11),\n'
        '                    margin=dict(l=40, r=20, t=30, b=30),\n'
        '                    height=250,\n'
        '                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),\n'
        '                    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),\n'
        '                )\n'
        '\n'
        '                trend_col1, trend_col2 = st.columns(2)\n'
        '\n'
        '                paces_list = [a.get("avg_pace_sec_per_km") for a in sorted_acts]\n'
        '                if any(pv is not None for pv in paces_list):\n'
        '                    with trend_col1:\n'
        '                        pace_vals, pace_dates = [], []\n'
        '                        for d, pv in zip(dates, paces_list):\n'
        '                            if pv and pv > 0:\n'
        '                                pace_vals.append(pv / 60)\n'
        '                                pace_dates.append(d)\n'
        '                        fig_pace = go.Figure()\n'
        '                        fig_pace.add_trace(go.Scatter(\n'
        '                            x=pace_dates, y=pace_vals,\n'
        '                            mode="lines+markers",\n'
        '                            line=dict(color="#00D26A", width=2),\n'
        '                            marker=dict(size=5),\n'
        '                            hovertemplate="%%{x}<br>%%{y:.2f} min/km<extra></extra>",\n'
        '                        ))\n'
        '                        fig_pace.update_layout(title="Average Pace (min/km)", yaxis_title="min/km", yaxis_autorange="reversed", **chart_layout)\n'
        '                        st.plotly_chart(fig_pace, use_container_width=True)\n'
        '\n'
        '                hr_list = [a.get("avg_hr") for a in sorted_acts]\n'
        '                if any(h is not None for h in hr_list):\n'
        '                    with trend_col2:\n'
        '                        hr_vals, hr_dates = [], []\n'
        '                        for d, hv in zip(dates, hr_list):\n'
        '                            if hv and hv > 0:\n'
        '                                hr_vals.append(hv)\n'
        '                                hr_dates.append(d)\n'
        '                        fig_hr = go.Figure()\n'
        '                        fig_hr.add_trace(go.Scatter(\n'
        '                            x=hr_dates, y=hr_vals,\n'
        '                            mode="lines+markers",\n'
        '                            line=dict(color="#FF6B6B", width=2),\n'
        '                            marker=dict(size=5),\n'
        '                            hovertemplate="%%{x}<br>%%{y} bpm<extra></extra>",\n'
        '                        ))\n'
        '                        fig_hr.update_layout(title="Average Heart Rate (bpm)", yaxis_title="bpm", **chart_layout)\n'
        '                        st.plotly_chart(fig_hr, use_container_width=True)\n'
        '\n'
        '                trend_col3, trend_col4 = st.columns(2)\n'
        '\n'
        '                cadence_list = [a.get("avg_running_cadence") for a in sorted_acts]\n'
        '                if any(cv is not None for cv in cadence_list):\n'
        '                    with trend_col3:\n'
        '                        cad_vals, cad_dates = [], []\n'
        '                        for d, cv in zip(dates, cadence_list):\n'
        '                            if cv and cv > 0:\n'
        '                                cad_vals.append(cv)\n'
        '                                cad_dates.append(d)\n'
        '                        fig_cad = go.Figure()\n'
        '                        fig_cad.add_trace(go.Scatter(\n'
        '                            x=cad_dates, y=cad_vals,\n'
        '                            mode="lines+markers",\n'
        '                            line=dict(color="#4ECDC4", width=2),\n'
        '                            marker=dict(size=5),\n'
        '                            hovertemplate="%%{x}<br>%%{y:.0f} spm<extra></extra>",\n'
        '                        ))\n'
        '                        fig_cad.update_layout(title="Running Cadence (spm)", yaxis_title="spm", **chart_layout)\n'
        '                        st.plotly_chart(fig_cad, use_container_width=True)\n'
        '\n'
        '                vo2_list = [a.get("vo2_max_value") for a in sorted_acts]\n'
        '                if any(v is not None for v in vo2_list):\n'
        '                    with trend_col4:\n'
        '                        vo2_vals, vo2_dates = [], []\n'
        '                        for d, vv in zip(dates, vo2_list):\n'
        '                            if vv and vv > 0:\n'
        '                                vo2_vals.append(vv)\n'
        '                                vo2_dates.append(d)\n'
        '                        fig_vo2 = go.Figure()\n'
        '                        fig_vo2.add_trace(go.Scatter(\n'
        '                            x=vo2_dates, y=vo2_vals,\n'
        '                            mode="lines+markers",\n'
        '                            line=dict(color="#FFE66D", width=2),\n'
        '                            marker=dict(size=5),\n'
        '                            hovertemplate="%%{x}<br>%%{y:.1f}<extra></extra>",\n'
        '                        ))\n'
        '                        fig_vo2.update_layout(title="VO2 Max Trend", yaxis_title="VO2 Max", **chart_layout)\n'
        '                        st.plotly_chart(fig_vo2, use_container_width=True)\n'
        '\n'
        '            st.markdown("")'
    )
    c = _replace(c, old_section, new_section, "Progress Trends replacing Recent Activities")
    p.write_text(c, encoding="utf-8")

if __name__ == "__main__":
    print("Applying all PaceForge changes...\n")
    apply_models()
    apply_garmin()
    apply_api()
    apply_planner()
    apply_dashboard()
    print(f"\nDone: {OK} OK, {FAIL} FAIL")
    if FAIL:
        sys.exit(1)
