#!/usr/bin/env python3
"""
Hermes Analytics — Streamlit Dashboard

Multi-page dashboard reading from the Hermes Analytics REST API.
Run with:
    streamlit run dashboard.py
    API_BASE_URL=http://my-server:5555 streamlit run dashboard.py
"""

import json
import os
from datetime import datetime, timezone

import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Hermes Analytics",
    page_icon="📊",
    layout="wide",
)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5555")


# ──────────────────────────────────────────────────────────────────────
# Shared Data Loading
# ──────────────────────────────────────────────────────────────────────

def load_snapshot():
    """Fetch snapshot from API, store in session state. Called once per session."""
    if "snapshot_loaded" in st.session_state:
        return

    st.session_state.snapshot_loaded = True
    st.session_state.snapshot = None
    st.session_state.api_error = None

    try:
        resp = requests.get(f"{API_BASE_URL}/api/snapshots/latest", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.snapshot = data
        elif resp.status_code == 503:
            st.session_state.api_error = "No snapshot data available. Run the collector to generate data."
        else:
            st.session_state.api_error = f"API returned status {resp.status_code}: {resp.text[:200]}"
    except requests.ConnectionError:
        st.session_state.api_error = (
            f"Cannot connect to Hermes Analytics API at {API_BASE_URL}. "
            "Make sure the server is running."
        )
    except requests.RequestException as e:
        st.session_state.api_error = f"API request failed: {e}"


def get_snapshot():
    """Return the cached snapshot or None."""
    return st.session_state.get("snapshot")


def get_sessions():
    """Return sessions from snapshot, or empty list."""
    snap = get_snapshot()
    if not snap:
        return []
    return snap.get("sessions", [])


def get_global_insights():
    """Return global_insights from snapshot, or empty dict."""
    snap = get_snapshot()
    if not snap:
        return {}
    return snap.get("global_insights", {})


# ──────────────────────────────────────────────────────────────────────
# Shared Helpers
# ──────────────────────────────────────────────────────────────────────

def show_api_error():
    """If there's an API error, show a banner and return True."""
    err = st.session_state.get("api_error")
    if err:
        st.warning(err, icon="⚠️")
        return True
    return False


def compute_duration(started_at, ended_at):
    """Compute human-readable duration between two ISO timestamps."""
    if not started_at or not ended_at:
        return "—"
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        # Handle both with and without microseconds
        for f in (fmt, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                start = datetime.strptime(started_at.replace("Z", ""), f)
                break
            except ValueError:
                continue
        else:
            return "—"
        for f in (fmt, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                end = datetime.strptime(ended_at.replace("Z", ""), f)
                break
            except ValueError:
                continue
        else:
            return "—"
        delta = end - start
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m {total_seconds % 60}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    except Exception:
        return "—"


def compute_total_tokens(tokens: dict) -> int:
    """Sum all token fields."""
    if not tokens:
        return 0
    return sum(v for v in tokens.values() if isinstance(v, (int, float)))


def format_timestamp(ts: str | None) -> str:
    """Format ISO timestamp for display."""
    if not ts:
        return "—"
    try:
        # Handle float (epoch seconds) and ISO strings
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)[:16] if len(str(ts)) >= 16 else str(ts)


def extract_date(ts) -> str:
    """Extract YYYY-MM-DD date from any timestamp type (str, int, float)."""
    if not ts:
        return ""
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        s = str(ts)
        return s[:10] if len(s) >= 10 else s


# ──────────────────────────────────────────────────────────────────────
# Page: Portal Home
# ──────────────────────────────────────────────────────────────────────

def page_portal():
    st.header("🏠 Hermes Analytics Portal")

    if show_api_error():
        st.info("No data available. Run the collector and refresh.", icon="ℹ️")
        return

    snap = get_snapshot()
    if not snap:
        st.info("No data available. Run the collector and refresh.", icon="ℹ️")
        return

    sessions = get_sessions()
    insights = get_global_insights()

    # Summary cards row
    total_sessions = len(sessions)
    total_messages = sum(s.get("stats", {}).get("message_count", 0) for s in sessions)
    total_skill_loads = sum(len(s.get("skills_loaded", [])) for s in sessions)
    total_tool_calls = sum(
        sum(t.get("count", 0) for t in s.get("tool_calls", [])) for s in sessions
    )
    models = set(s.get("model") for s in sessions if s.get("model"))
    platforms = set(s.get("platform") for s in sessions if s.get("platform"))
    generated_at = snap.get("generated_at", "—")

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Sessions", total_sessions)
    col2.metric("Messages", f"{total_messages:,}")
    col3.metric("Skill Loads", total_skill_loads)
    col4.metric("Tool Calls", f"{total_tool_calls:,}")
    col5.metric("Models", len(models))
    col6.metric("Platforms", len(platforms))
    col7.metric("Updated", format_timestamp(generated_at))

    st.divider()

    # Top skills and tools preview
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🔝 Top Skills")
        skills = insights.get("skills", [])
        if not skills:
            # Compute from sessions
            skills = _compute_skills_from_sessions(sessions)
        if skills:
            top_skills = skills[:5]
            skill_data = [
                {"Rank": i + 1, "Skill": s["name"], "Loads": s.get("load_count", 0)}
                for i, s in enumerate(top_skills)
            ]
            st.dataframe(skill_data, width='stretch', hide_index=True)
            if len(skills) > 5:
                st.caption(f"…and {len(skills) - 5} more. **View all → Skills** in sidebar.")
        else:
            st.caption("No skills data.")

    with col_right:
        st.subheader("🔧 Top Tools")
        tools = insights.get("tools", [])
        if not tools:
            tools = _compute_tools_from_sessions(sessions)
        if tools:
            top_tools = tools[:5]
            tool_data = [
                {"Rank": i + 1, "Tool": t["name"], "Calls": t.get("count", 0)}
                for i, t in enumerate(top_tools)
            ]
            st.dataframe(tool_data, width='stretch', hide_index=True)
            if len(tools) > 5:
                st.caption(f"…and {len(tools) - 5} more. **View all → Tools** in sidebar.")
        else:
            st.caption("No tools data.")


# ──────────────────────────────────────────────────────────────────────
# Page: Session Overview
# ──────────────────────────────────────────────────────────────────────

def page_session_overview():
    st.header("📋 Session Overview")

    if show_api_error():
        return

    sessions = get_sessions()
    if not sessions:
        st.info("No sessions found. Run the collector to generate data.", icon="ℹ️")
        return

    # Filters
    models_list = sorted(set(s.get("model") for s in sessions if s.get("model")))
    platforms_list = sorted(set(s.get("platform") for s in sessions if s.get("platform")))

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_model = st.selectbox(
            "Filter by Model", ["All"] + models_list, key="filter_model"
        )
    with col_f2:
        selected_platform = st.selectbox(
            "Filter by Platform", ["All"] + platforms_list, key="filter_platform"
        )

    # Apply filters
    filtered = sessions
    if selected_model != "All":
        filtered = [s for s in filtered if s.get("model") == selected_model]
    if selected_platform != "All":
        filtered = [s for s in filtered if s.get("platform") == selected_platform]

    # Summary cards
    total_filtered = len(filtered)
    total_msgs = sum(s.get("stats", {}).get("message_count", 0) for s in filtered)
    total_skills = sum(len(s.get("skills_loaded", [])) for s in filtered)
    total_tools = sum(
        sum(t.get("count", 0) for t in s.get("tool_calls", [])) for s in filtered
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filtered Sessions", total_filtered)
    c2.metric("Messages", f"{total_msgs:,}")
    c3.metric("Skill Loads", total_skills)
    c4.metric("Tool Calls", f"{total_tools:,}")

    st.divider()

    # Charts row
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Sessions per Day")
        date_counts = {}
        for s in filtered:
            started = s.get("started_at", "")
            date_key = extract_date(started) or "unknown"
            date_counts[date_key] = date_counts.get(date_key, 0) + 1
        if date_counts:
            dates_sorted = sorted(date_counts.keys())
            fig = px.bar(
                x=dates_sorted,
                y=[date_counts[d] for d in dates_sorted],
                labels={"x": "Date", "y": "Sessions"},
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, width='stretch')

    with col_chart2:
        st.subheader("Sessions by Model")
        model_counts = {}
        for s in filtered:
            m = s.get("model", "unknown")
            model_counts[m] = model_counts.get(m, 0) + 1
        if model_counts:
            items = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)
            fig = px.bar(
                x=[v for _, v in items],
                y=[k for k, _ in items],
                orientation="h",
                labels={"x": "Sessions", "y": "Model"},
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, width='stretch')

    st.divider()

    # Session table
    st.subheader(f"Sessions ({len(filtered)})")
    table_data = []
    for s in filtered:
        sid = s.get("session_id", "—")
        total_tokens = compute_total_tokens(s.get("tokens", {}))
        table_data.append({
            "session_id": str(sid)[:30] if sid else "—",
            "model": s.get("model", "—"),
            "platform": s.get("platform", "—"),
            "started_at": format_timestamp(s.get("started_at")),
            "duration": compute_duration(s.get("started_at"), s.get("ended_at")),
            "tokens": total_tokens,
            "skills": len(s.get("skills_loaded", [])),
            "tools": sum(t.get("count", 0) for t in s.get("tool_calls", [])),
            "messages": s.get("stats", {}).get("message_count", 0),
        })

    # Session selection via dataframe
    event = st.dataframe(
        table_data,
        width='stretch',
        hide_index=True,
        column_config={
            "session_id": st.column_config.TextColumn("Session ID"),
            "model": st.column_config.TextColumn("Model"),
            "platform": st.column_config.TextColumn("Platform"),
            "started_at": st.column_config.TextColumn("Started"),
            "duration": st.column_config.TextColumn("Duration"),
            "tokens": st.column_config.NumberColumn("Tokens"),
            "skills": st.column_config.NumberColumn("Skills"),
            "tools": st.column_config.NumberColumn("Tool Calls"),
            "messages": st.column_config.NumberColumn("Messages"),
        },
        on_select="rerun",
        selection_mode="single-row",
    )

    # Handle row click — navigate to session detail
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        if selected_idx < len(filtered):
            st.session_state.selected_session_id = filtered[selected_idx].get(
                "session_id"
            )
            st.toast("Session selected! Click '🔍 Session Detail' in the sidebar to view it.", icon="✅")


# ──────────────────────────────────────────────────────────────────────
# Page: Session Detail
# ──────────────────────────────────────────────────────────────────────

def page_session_detail():
    st.header("🔍 Session Detail")

    if show_api_error():
        return

    sessions = get_sessions()
    sid = st.session_state.get("selected_session_id")

    # Also allow selecting session from dropdown
    session_options = {s.get("session_id"): f"{s.get('session_id', '—')[:30]} — {format_timestamp(s.get('started_at'))}" for s in sessions}
    if not sid and sessions:
        st.info("Select a session from the overview page, or pick one below:", icon="👆")

    col_btn, col_select = st.columns([1, 3])
    with col_btn:
        if st.button("← Back to Sessions", width='stretch'):
            st.session_state.selected_session_id = None
            st.rerun()
    with col_select:
        selected = st.selectbox(
            "Or select a session:",
            options=[""] + list(session_options.keys()),
            format_func=lambda x: session_options.get(x, "—") if x else "— Choose a session —",
            key="detail_session_select",
        )
        if selected:
            sid = selected
            st.session_state.selected_session_id = sid

    if not sid:
        st.info("No session selected. Click a session in the Session Overview page.", icon="👆")
        return

    # Find the session
    session = next((s for s in sessions if s.get("session_id") == sid), None)
    if not session:
        st.error(f"Session not found: {sid}")
        return

    st.session_state.selected_session_id = sid

    # ── Header ──
    st.subheader(f"Session: {str(sid)[:50]}")
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    col_m1.metric("Model", session.get("model", "—"))
    col_m2.metric("Platform", session.get("platform", "—"))
    col_m3.metric("Started", format_timestamp(session.get("started_at")))
    col_m4.metric("Ended", format_timestamp(session.get("ended_at")))
    col_m5.metric(
        "Duration",
        compute_duration(session.get("started_at"), session.get("ended_at")),
    )

    st.divider()

    # ── Token Usage ──
    st.subheader("🔢 Token Usage")
    tokens = session.get("tokens", {})
    if tokens:
        total_tokens = compute_total_tokens(tokens)
        token_cols = st.columns(6)
        token_fields = [
            ("Input", "input"), ("Output", "output"), ("Cache Read", "cache_read"),
            ("Cache Write", "cache_write"), ("Reasoning", "reasoning"), ("Total", None),
        ]
        for col, (label, key) in zip(token_cols, token_fields):
            if key is None:
                col.metric(label, f"{total_tokens:,}")
            else:
                col.metric(label, f"{tokens.get(key, 0):,}")
    else:
        st.caption("No token data available.")

    st.divider()

    # ── Skills vs Tools visual ──
    col_v1, col_v2 = st.columns(2)
    skills_loaded = session.get("skills_loaded", [])
    tool_calls = session.get("tool_calls", [])
    skill_names = [s.get("skill_name", "unknown") for s in skills_loaded]
    tool_names_list = []
    for t in tool_calls:
        for _ in range(t.get("count", 0)):
            tool_names_list.append(t.get("tool_name", "unknown"))

    with col_v1:
        st.metric("Skills Loaded", len(skills_loaded))
        if skill_names:
            skill_counts = {}
            for n in skill_names:
                skill_counts[n] = skill_counts.get(n, 0) + 1
            items = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
            fig = px.bar(
                x=[v for _, v in items],
                y=[k for k, _ in items],
                orientation="h",
                labels={"x": "Loads", "y": "Skill"},
                title="Skills Loaded",
            )
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250)
            st.plotly_chart(fig, width='stretch')

    with col_v2:
        st.metric("Tool Calls", sum(t.get("count", 0) for t in tool_calls))
        if tool_names_list:
            tool_counts = {}
            for n in tool_names_list:
                tool_counts[n] = tool_counts.get(n, 0) + 1
            items = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
            fig = px.bar(
                x=[v for _, v in items],
                y=[k for k, _ in items],
                orientation="h",
                labels={"x": "Calls", "y": "Tool"},
                title="Tool Calls",
            )
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=250)
            st.plotly_chart(fig, width='stretch')

    st.divider()

    # ── Skills Table ──
    st.subheader("🧠 Skills Loaded")
    if skills_loaded:
        skill_rows = []
        for sk in skills_loaded:
            skill_rows.append({
                "Skill": sk.get("skill_name", "unknown"),
                "Chars": sk.get("content_chars", 0),
                "Tokens (est.)": sk.get("token_estimate", 0),
                "Preceding Message": (sk.get("preceding_user_message") or "")[:100],
                "Timestamp": format_timestamp(sk.get("load_timestamp")),
            })
        st.dataframe(skill_rows, width='stretch', hide_index=True)
    else:
        st.caption("No skills loaded in this session.")

    # ── Tool Calls Table ──
    st.subheader("🔧 Tool Calls")
    if tool_calls:
        tool_rows = []
        for tc in tool_calls:
            tool_rows.append({
                "Tool": tc.get("tool_name", "unknown"),
                "Count": tc.get("count", 0),
                "Message IDs": len(tc.get("message_ids", [])),
            })
        st.dataframe(tool_rows, width='stretch', hide_index=True)
    else:
        st.caption("No tool calls in this session.")

    # ── Shell Commands ──
    st.subheader("💻 Shell Commands")
    shell_cmds = session.get("shell_commands", [])
    if shell_cmds:
        shell_rows = []
        for sc in shell_cmds:
            exit_code = sc.get("exit_code")
            success_icon = "✅" if sc.get("success") else ("❌" if sc.get("success") is False else "—")
            shell_rows.append({
                "Command": sc.get("command", "")[:120],
                "Exit": str(exit_code) if exit_code is not None else "—",
                "Result": success_icon,
                "Timestamp": format_timestamp(sc.get("timestamp")),
            })
        st.dataframe(shell_rows, width='stretch', hide_index=True)
    else:
        st.caption("No shell commands in this session.")

    # ── User Messages ──
    st.subheader("💬 User Messages")
    user_msgs = session.get("user_messages", [])
    if user_msgs:
        for um in user_msgs:
            ts = format_timestamp(um.get("timestamp"))
            content = um.get("content", "")[:300]
            st.markdown(f"**{ts}** — {content}")
    else:
        st.caption("No user messages in this session.")

    # ── Errors ──
    st.subheader("⚠️ Errors")
    errors = session.get("errors", [])
    if errors:
        for err in errors:
            st.error(
                f"{format_timestamp(err.get('timestamp'))} — "
                f"{err.get('related_to', 'Error')} "
                f"({err.get('duration_s', 0):.1f}s)"
            )
    else:
        st.caption("No errors in this session.")


# ──────────────────────────────────────────────────────────────────────
# Page: Skills Dashboard
# ──────────────────────────────────────────────────────────────────────

def page_skills():
    st.header("⭐ Skills Analytics")

    if show_api_error():
        return

    sessions = get_sessions()
    insights = get_global_insights()

    skills = insights.get("skills", [])
    if not skills:
        skills = _compute_skills_from_sessions(sessions)

    if not skills:
        st.info("No skills data available.", icon="ℹ️")
        return

    # Charts row
    col_ch1, col_ch2 = st.columns(2)

    with col_ch1:
        st.subheader("Top Skills by Load Count")
        top_n = st.checkbox("Show all skills", value=False, key="skills_show_all")
        display = skills if top_n else skills[:10]
        fig = px.bar(
            x=[s.get("load_count", 0) for s in display],
            y=[s.get("name", "unknown") for s in display],
            orientation="h",
            labels={"x": "Load Count", "y": "Skill"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=max(300, len(display) * 22))
        st.plotly_chart(fig, width='stretch')

    with col_ch2:
        st.subheader("Token Estimate Distribution")
        token_vals = [
            s.get("token_estimate", 0)
            for s in skills
            if s.get("token_estimate", 0) > 0
        ] if "token_estimate" in (skills[0] if skills else {}) else [
            s.get("load_count", 0) * 500 for s in skills
        ]
        if token_vals:
            fig = px.histogram(
                x=token_vals,
                nbins=min(20, len(token_vals)),
                labels={"x": "Token Estimate", "y": "Frequency"},
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, width='stretch')
        else:
            st.caption("No token data available.")

    st.divider()

    # Skills usage timeline
    st.subheader("Skills Usage Timeline")
    skill_timeline = {}
    for sess in sessions:
        date_key = extract_date(sess.get("started_at"))
        if not date_key:
            continue
        for sk in sess.get("skills_loaded", []):
            name = sk.get("skill_name", "unknown")
            if name not in skill_timeline:
                skill_timeline[name] = {}
            skill_timeline[name][date_key] = skill_timeline[name].get(date_key, 0) + 1

    if skill_timeline:
        all_dates = sorted(set(d for counts in skill_timeline.values() for d in counts))
        top_skills_for_timeline = sorted(
            skill_timeline.keys(),
            key=lambda k: sum(skill_timeline[k].values()),
            reverse=True,
        )[:8]
        fig = go.Figure()
        for name in top_skills_for_timeline:
            counts = [skill_timeline[name].get(d, 0) for d in all_dates]
            fig.add_trace(go.Bar(name=name, x=all_dates, y=counts))
        fig.update_layout(
            barmode="stack",
            margin=dict(l=0, r=0, t=0, b=0),
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, width='stretch')

    st.divider()

    # Ranking table
    st.subheader("Skills Ranking")
    rank_data = []
    for i, s in enumerate(skills):
        load_count = s.get("load_count", 0)
        total_chars = s.get("total_chars", 0)
        token_estimate = s.get("token_estimate", 0)
        rank_data.append({
            "Rank": i + 1,
            "Skill": s.get("name", "unknown"),
            "Loads": load_count,
            "Total Chars": f"{total_chars:,}",
            "Tokens (est.)": f"{token_estimate:,}",
            "Avg Chars/Load": f"{total_chars / load_count:.0f}" if load_count > 0 else "0",
            "Avg Tokens/Load": f"{token_estimate / load_count:.0f}" if load_count > 0 else "0",
        })
    st.dataframe(rank_data, width='stretch', hide_index=True)

    # Skill drill-down
    st.divider()
    st.subheader("🔎 Skill Drill-Down")
    skill_names_list = [s.get("name", "unknown") for s in skills]
    selected_skill = st.selectbox(
        "Select a skill to see sessions that loaded it:",
        options=[""] + skill_names_list,
        key="skill_drilldown",
    )
    if selected_skill:
        matching_sessions = []
        for sess in sessions:
            for sk in sess.get("skills_loaded", []):
                if sk.get("skill_name") == selected_skill:
                    preceding = (sk.get("preceding_user_message") or "")[:100]
                    matching_sessions.append({
                        "Session ID": str(sess.get("session_id", "—"))[:30],
                        "Date": format_timestamp(sess.get("started_at")),
                        "Platform": sess.get("platform", "—"),
                        "Preceding Message": preceding,
                    })
                    break
        if matching_sessions:
            st.write(f"**{len(matching_sessions)} sessions** loaded **{selected_skill}**:")
            st.dataframe(matching_sessions, width='stretch', hide_index=True)
        else:
            st.caption(f"No sessions found for skill: {selected_skill}")

    # Preceding messages
    st.divider()
    st.subheader("💬 Most Common Preceding Messages")
    msg_counts = {}
    for sess in sessions:
        for sk in sess.get("skills_loaded", []):
            msg = sk.get("preceding_user_message")
            if msg:
                truncated = msg[:80]
                msg_counts[truncated] = msg_counts.get(truncated, 0) + 1
    if msg_counts:
        top_msgs = sorted(msg_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        msg_data = [
            {"Count": c, "Message": m} for m, c in top_msgs
        ]
        st.dataframe(msg_data, width='stretch', hide_index=True)
    else:
        st.caption("No preceding user messages found.")


# ──────────────────────────────────────────────────────────────────────
# Page: Tools Dashboard
# ──────────────────────────────────────────────────────────────────────

def page_tools():
    st.header("🔧 Tools Analytics")

    if show_api_error():
        return

    sessions = get_sessions()
    insights = get_global_insights()

    tools = insights.get("tools", [])
    if not tools:
        tools = _compute_tools_from_sessions(sessions)

    if not tools:
        st.info("No tools data available.", icon="ℹ️")
        return

    total_calls = sum(t.get("count", 0) for t in tools)

    # Charts row
    col_ch1, col_ch2 = st.columns(2)

    with col_ch1:
        st.subheader("Tools by Call Count")
        fig = px.bar(
            x=[t.get("count", 0) for t in tools],
            y=[t.get("name", "unknown") for t in tools],
            orientation="h",
            labels={"x": "Call Count", "y": "Tool"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=max(300, len(tools) * 22))
        st.plotly_chart(fig, width='stretch')

    with col_ch2:
        st.subheader("Tool Call Distribution")
        if len(tools) > 1:
            fig = px.pie(
                values=[t.get("count", 0) for t in tools],
                names=[t.get("name", "unknown") for t in tools],
                hole=0.4,
            )
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350)
            st.plotly_chart(fig, width='stretch')
        else:
            st.caption("Only one tool — cannot render distribution.")

    st.divider()

    # Tools usage timeline
    st.subheader("Tools Usage Timeline")
    tool_timeline = {}
    for sess in sessions:
        date_key = extract_date(sess.get("started_at"))
        if not date_key:
            continue
        for tc in sess.get("tool_calls", []):
            name = tc.get("tool_name", "unknown")
            if name not in tool_timeline:
                tool_timeline[name] = {}
            tool_timeline[name][date_key] = (
                tool_timeline[name].get(date_key, 0) + tc.get("count", 0)
            )

    if tool_timeline:
        all_dates = sorted(set(d for counts in tool_timeline.values() for d in counts))
        top_tools_series = sorted(
            tool_timeline.keys(),
            key=lambda k: sum(tool_timeline[k].values()),
            reverse=True,
        )[:8]
        fig = go.Figure()
        for name in top_tools_series:
            counts = [tool_timeline[name].get(d, 0) for d in all_dates]
            fig.add_trace(go.Bar(name=name, x=all_dates, y=counts))
        fig.update_layout(
            barmode="stack",
            margin=dict(l=0, r=0, t=0, b=0),
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, width='stretch')

    st.divider()

    # Tool call distribution histogram
    st.subheader("Tool Call Counts per Session")
    tool_counts_per_session = []
    for sess in sessions:
        cnt = sum(t.get("count", 0) for t in sess.get("tool_calls", []))
        tool_counts_per_session.append(cnt)
    if tool_counts_per_session:
        fig = px.histogram(
            x=tool_counts_per_session,
            nbins=min(20, len(tool_counts_per_session)),
            labels={"x": "Tool Calls", "y": "Sessions"},
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
        st.plotly_chart(fig, width='stretch')

    st.divider()

    # Ranking table
    st.subheader("Tools Ranking")
    rank_data = []
    for i, t in enumerate(tools):
        count = t.get("count", 0)
        pct = (count / total_calls * 100) if total_calls > 0 else 0
        rank_data.append({
            "Rank": i + 1,
            "Tool": t.get("name", "unknown"),
            "Calls": count,
            "% of Total": f"{pct:.1f}%",
        })
    st.dataframe(rank_data, width='stretch', hide_index=True)

    # Tool drill-down
    st.divider()
    st.subheader("🔎 Tool Drill-Down")
    tool_names_list = [t.get("name", "unknown") for t in tools]
    selected_tool = st.selectbox(
        "Select a tool to see sessions that used it:",
        options=[""] + tool_names_list,
        key="tool_drilldown",
    )
    if selected_tool:
        matching_sessions = []
        for sess in sessions:
            for tc in sess.get("tool_calls", []):
                if tc.get("tool_name") == selected_tool:
                    matching_sessions.append({
                        "Session ID": str(sess.get("session_id", "—"))[:30],
                        "Date": format_timestamp(sess.get("started_at")),
                        "Model": sess.get("model", "—"),
                        "Tool Calls": tc.get("count", 0),
                    })
                    break
        if matching_sessions:
            st.write(f"**{len(matching_sessions)} sessions** used **{selected_tool}**:")
            st.dataframe(matching_sessions, width='stretch', hide_index=True)
        else:
            st.caption(f"No sessions found for tool: {selected_tool}")


# ──────────────────────────────────────────────────────────────────────
# Fallback Computation Helpers
# ──────────────────────────────────────────────────────────────────────

def _compute_skills_from_sessions(sessions):
    """Compute skills ranking from session data when global_insights is missing."""
    agg = {}
    for sess in sessions:
        for sk in sess.get("skills_loaded", []):
            name = sk.get("skill_name", "unknown")
            if name not in agg:
                agg[name] = {"name": name, "load_count": 0, "total_chars": 0, "token_estimate": 0}
            agg[name]["load_count"] += 1
            agg[name]["total_chars"] += sk.get("content_chars", 0)
            agg[name]["token_estimate"] += sk.get("token_estimate", 0)
    return sorted(agg.values(), key=lambda x: x["load_count"], reverse=True)


def _compute_tools_from_sessions(sessions):
    """Compute tools ranking from session data when global_insights is missing."""
    agg = {}
    for sess in sessions:
        for tc in sess.get("tool_calls", []):
            name = tc.get("tool_name", "unknown")
            agg[name] = agg.get(name, 0) + tc.get("count", 0)
    return [{"name": k, "count": v} for k, v in sorted(agg.items(), key=lambda x: x[1], reverse=True)]


# ──────────────────────────────────────────────────────────────────────
# Navigation Setup
# ──────────────────────────────────────────────────────────────────────

# Load data once at startup
load_snapshot()

# Build pages
portal_page = st.Page(
    page_portal, title="Home", icon="🏠", default=True
)
overview_page = st.Page(
    page_session_overview, title="Session Overview", icon="📋", url_path="session_overview"
)
detail_page = st.Page(
    page_session_detail, title="Session Detail", icon="🔍", url_path="session_detail"
)
skills_page = st.Page(
    page_skills, title="Skills", icon="⭐", url_path="skills"
)
tools_page = st.Page(
    page_tools, title="Tools", icon="🔧", url_path="tools"
)

nav = st.navigation(
    {"Main": [portal_page, overview_page, detail_page, skills_page, tools_page]}
)
nav.run()
