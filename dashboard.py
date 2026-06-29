#!/usr/bin/env python3
"""
Hermes Analytics — Local Single-User Streamlit Dashboard

Reads from the local single-user REST API.
Run by the /hermes-snapshot-analytics slash command.
Includes a "🛑 Shutdown Analytics" button in the sidebar.
"""

import json
import os
import signal
import time
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
# Shutdown Helpers
# ──────────────────────────────────────────────────────────────────────

SERVER_PID_FILE = "/tmp/hermes-analytics-server.pid"
DASHBOARD_PID_FILE = "/tmp/hermes-analytics-dashboard.pid"


def _kill_from_pid_file(pid_file: str) -> bool:
    """Read PID from file, send SIGTERM, then SIGKILL if still alive."""
    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)  # force kill if still alive
        except OSError:
            pass  # already dead
        os.remove(pid_file)
        return True
    except OSError:
        return False


def shutdown_analytics():
    """Kill server + dashboard processes. Then stop the Streamlit app."""
    _kill_from_pid_file(SERVER_PID_FILE)
    _kill_from_pid_file(DASHBOARD_PID_FILE)
    st.success("✅ Analytics server and dashboard shut down.")
    st.stop()


# ──────────────────────────────────────────────────────────────────────
# Shared Data Loading
# ──────────────────────────────────────────────────────────────────────

def load_snapshot():
    """Fetch snapshot from the local single-user API. Called once per session."""
    if "snapshot_loaded" in st.session_state:
        return

    st.session_state.snapshot_loaded = True
    st.session_state.snapshot = None
    st.session_state.api_error = None

    try:
        resp = requests.get(f"{API_BASE_URL}/api/snapshots/latest", timeout=10)
        if resp.status_code == 200:
            st.session_state.snapshot = resp.json()
        elif resp.status_code == 503:
            st.session_state.api_error = "No snapshot data available. Push a snapshot via the collector first."
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
    """Compute human-readable duration between timestamps (ISO strings or Unix epoch)."""
    if not started_at or not ended_at:
        return "—"
    try:
        # Handle Unix epoch floats/ints
        if isinstance(started_at, (int, float)):
            start = datetime.fromtimestamp(started_at, tz=timezone.utc)
        else:
            start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        if isinstance(ended_at, (int, float)):
            end = datetime.fromtimestamp(ended_at, tz=timezone.utc)
        else:
            end = datetime.fromisoformat(str(ended_at).replace("Z", "+00:00"))
        delta = end - start
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return "—"
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


def golden_ratio_colors(n: int) -> list[str]:
    """Generate N perceptually distinct colors using the Golden Ratio conjugate.
    
    Uses HSL color space with hue = (i * phi_inv) mod 1, saturation=70%, lightness=50%.
    Maximizes perceptual distance between adjacent colors for any N.
    """
    phi_inv = 0.618033988749895
    colors = []
    for i in range(n):
        hue = (i * phi_inv) % 1.0
        colors.append(f"hsl({hue * 360:.0f}, 70%, 50%)")
    return colors


def chart_layout(**kwargs):
    """Return common chart layout with legend below and bar gaps."""
    defaults = dict(
        margin=dict(l=0, r=0, t=0, b=40),
        legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
    )
    defaults.update(kwargs)
    return defaults


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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sessions", total_sessions)
    col2.metric("Messages", f"{total_messages:,}")
    col3.metric("Skill Loads", total_skill_loads)
    col4.metric("Tool Calls", f"{total_tool_calls:,}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Models", len(models))
    col2.metric("Platforms", len(platforms))
    col3.metric("Updated", str(extract_date(generated_at)))
    col4.empty()

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
                st.caption(f"…and {len(skills) - 5} more.")
                # Native link that routes to your skills_page object
                st.page_link(skills_page, label="View all Skills →", icon="⭐")
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
                st.caption(f"…and {len(tools) - 5} more.")
                # Native link that routes to your tools_page object
                st.page_link(tools_page, label="View all Tools →", icon="🔧")
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
            fig.update_layout(bargap=0.15, margin=dict(l=0, r=0, t=0, b=0), height=300)
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
            fig.update_layout(bargap=0.15, margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, width='stretch')

    st.divider()

    # Session table with View button per row
    st.subheader(f"Sessions ({len(filtered)})")
    st.caption("Click **→ View** to jump directly to the session detail page.")

    # Header row
    with st.container(border=True):
        # Adjusted ratios to give Started and Duration the room they need
        hcols = st.columns([0.6, 2.5, 2.0, 1.0, 1.6, 1.1, 0.8, 0.7, 0.7, 0.7])
        hcols[0].markdown("**View**")
        hcols[1].markdown("**Title**")
        hcols[2].markdown("**Model**")
        hcols[3].markdown("**Platform**")
        hcols[4].markdown("**Started**")
        hcols[5].markdown("**Duration**")
        hcols[6].markdown("**Tokens**")
        hcols[7].markdown("**Skills**")
        hcols[8].markdown("**Tools**")
        hcols[9].markdown("**Msgs**")

    for s in filtered:
        sid = s.get("session_id")
        total_tokens = int(compute_total_tokens(s.get("tokens", {})))
        with st.container(border=True):
            cols = st.columns([0.6, 2.5, 2.0, 1.0, 1.6, 1.1, 0.8, 0.7, 0.7, 0.7])
            with cols[0]:
                if st.button("→", key=f"view_{sid}", use_container_width=True):
                    st.session_state.selected_session_id = sid
                    st.switch_page(detail_page)
            
            # Removed the nowrap HTML spans so text behaves normally
            cols[1].write((s.get("chat_name") or "Untitled")[:80])
            cols[2].write(str(s.get("model", "—"))[:50])
            cols[3].write(str(s.get("platform", "—")))
            cols[4].write(format_timestamp(s.get("started_at")))
            cols[5].write(compute_duration(s.get("started_at"), s.get("ended_at")))
            cols[6].write(str(total_tokens))
            cols[7].write(str(len(s.get('skills_loaded', []))))
            cols[8].write(str(sum(t.get('count', 0) for t in s.get('tool_calls', []))))
            cols[9].write(str(s.get('stats', {}).get('message_count', 0)))

# ──────────────────────────────────────────────────────────────────────
# Page: Session Detail
# ──────────────────────────────────────────────────────────────────────

def page_session_detail():
    # Inject JS to instantly reset scroll position
    # Inject an invisible anchor and pull it into view after a slight delay
    st.html(
        """
        <div id="session-detail"></div>
        <script>
            setTimeout(function() {
                var anchor = document.getElementById('session-detail');
                if (anchor) {
                    anchor.scrollIntoView({behavior: 'instant', block: 'start'});
                }
            }, 100); // 100ms delay beats Streamlit's native scroll restoration
        </script>
        """,
        unsafe_allow_javascript=True
    )
    
    st.header("🔍 Session Detail")

    if show_api_error():
        return

    sessions = get_sessions()
    sid = st.session_state.get("selected_session_id")

    # Auto-select latest session if none selected
    if not sid and sessions:
        sid = sessions[0].get("session_id")
        st.session_state.selected_session_id = sid

    # Also allow selecting session from dropdown
    session_options = {}
    for s in sessions:
        sid_key = s.get("session_id")
        title = s.get("chat_name") or "Untitled"
        label = f"{title} — {str(sid_key)[:20]} — {format_timestamp(s.get('started_at'))}"
        session_options[sid_key] = label

    col_btn, col_select = st.columns([1, 3])
    with col_btn:
        if st.button("← Back to Sessions", use_container_width=True):
            st.session_state.selected_session_id = None
            st.switch_page(overview_page)
    with col_select:
        selected = st.selectbox(
            "Select a session",
            options=list(session_options.keys()),
            format_func=lambda x: session_options.get(x, "—"),
            index=list(session_options.keys()).index(sid) if sid in session_options else 0,
            key="detail_session_select",
            label_visibility="collapsed",
        )
        if selected and selected != sid:
            sid = selected
            st.session_state.selected_session_id = sid

    # Find the session
    session = next((s for s in sessions if s.get("session_id") == sid), None)
    if not session:
        st.error(f"Session not found: {sid}")
        return

    # ── Header ──
    chat_name = session.get("chat_name") or ""
    heading = f"{chat_name}" if chat_name else f"Session: {str(sid)[:50]}"
    st.subheader(heading)
    if chat_name:
        st.caption(f"ID: {sid}")

    model = str(session.get("model", "—"))
    platform = session.get("platform", "—")
    duration = compute_duration(session.get("started_at"), session.get("ended_at"))
    started = format_timestamp(session.get("started_at"))
    ended = format_timestamp(session.get("ended_at"))

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.caption("Model")
        st.markdown(f"<span style='font-size: 1.8rem; font-weight: 600; line-height: 1.2;'>{model}</span>", unsafe_allow_html=True)
    col_m2.metric("Platform", platform)
    col_m3.metric("Duration", duration)
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Started", started)
    col_m2.metric("Ended", ended)
    # Show full model name below if it was truncated
    if len(model) > 30:
        st.caption(f"Full model: {model}")

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
            fig.update_layout(bargap=0.15, margin=dict(l=0, r=0, t=30, b=0), height=250)
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
            fig.update_layout(bargap=0.15, margin=dict(l=0, r=0, t=30, b=0), height=250)
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
            sr = tc.get("success_rate")
            sr_display = f"{sr * 100:.0f}%" if sr is not None else "—"
            tool_rows.append({
                "Tool": tc.get("tool_name", "unknown"),
                "Count": tc.get("count", 0),
                "Success Rate": sr_display,
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
            content = um.get("content", "")
            max_len = 300
            truncated = len(content) > max_len
            display_text = content[:max_len]
            if truncated:
                display_text += "… (truncated)"
            with st.container(border=True):
                st.caption(f"**{ts}**")
                st.markdown(display_text)
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
        fig.update_layout(bargap=0.15, margin=dict(l=0, r=0, t=0, b=0), height=max(300, len(display) * 22))
        st.plotly_chart(fig, width='stretch')

    with col_ch2:
        # 1. Clearer Title and Caption
        st.subheader("Skill Sizes (Token Footprint)")
        st.caption("Shows how many distinct skills fall into different size ranges.")
        
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
                nbins=40,
                labels={"x": "Skill Size (Tokens)", "y": "Number of Skills"},
            )
            
            # 2. Force the hover text to speak in plain English
            fig.update_traces(
                hovertemplate="<b>Size Range:</b> %{x} tokens<br><b>Skill Count:</b> %{y} skills<extra></extra>"
            )
            
            # 3. Explicit Axis Titles
            fig.update_layout(
                bargap=0.15, 
                margin=dict(l=0, r=0, t=0, b=0), 
                height=350,
                yaxis_title="Number of Distinct Skills",
                xaxis_title="Estimated Tokens per Skill"
            )
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
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
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
    # Default to most-loaded skill
    default_skill = skill_names_list[0] if skill_names_list else None
    selected_skill = st.selectbox(
        "Select a skill to see sessions that loaded it:",
        options=[""] + skill_names_list,
        index=1 if default_skill else 0,
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
                        "Session Title": sess.get("chat_name") or "Untitled",
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
        show_all_tools = st.checkbox("Show all tools", value=False, key="tools_show_all")
        display_tools = tools if show_all_tools else tools[:10]
        fig = px.bar(
            x=[t.get("count", 0) for t in display_tools],
            y=[t.get("name", "unknown") for t in display_tools],
            orientation="h",
            labels={"x": "Call Count", "y": "Tool"},
        )
        fig.update_layout(
            bargap=0.15,
            margin=dict(l=200, r=0, t=0, b=0),
            height=max(300, len(display_tools) * 22),
        )
        fig.update_yaxes(tickfont=dict(size=11))
        st.plotly_chart(fig, width='stretch')
        if not show_all_tools and len(tools) > 10:
            st.caption(f"Showing top 10 of {len(tools)} tools. Check 'Show all tools' to see everything.")

    with col_ch2:
        st.subheader("Tool Call Distribution")
        if len(tools) > 1:
            n_tools = len(tools)
            colors = golden_ratio_colors(n_tools)
            fig = px.pie(
                values=[t.get("count", 0) for t in tools],
                names=[t.get("name", "unknown") for t in tools],
                hole=0.4,
                color_discrete_sequence=colors,
            )
            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>%{value} calls (%{percent})<extra></extra>",
                textposition="inside",
                textinfo="percent",
            )
            fig.update_layout(
                margin=dict(l=20, r=20, t=0, b=0),
                height=400,
                showlegend=False,
            )
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
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5),
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
        fig.update_layout(bargap=0.15, margin=dict(l=0, r=0, t=0, b=0), height=300)
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
        index=1,
        key="tool_drilldown",
    )
    if selected_tool:
        matching_sessions = []
        for sess in sessions:
            for tc in sess.get("tool_calls", []):
                if tc.get("tool_name") == selected_tool:
                    matching_sessions.append({
                        "Session ID": str(sess.get("session_id", "—"))[:30],
                        "Session Title": sess.get("chat_name") or "Untitled",
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
# Log Payloads Data Helpers (for Mindlayer Skills page)
# ──────────────────────────────────────────────────────────────────────

def _get_log_payloads():
    """Return log_payloads.operations from snapshot, or empty list."""
    snap = get_snapshot()
    if not snap:
        return []
    lp = snap.get("log_payloads", {})
    return lp.get("operations", [])


def _fmt_duration(ms: int | None) -> str:
    """Format milliseconds to human-readable string (matching telemetry server)."""
    if ms is None or ms <= 0:
        return "0s"
    if ms < 1000:
        return f"{ms}ms"
    s = ms / 1000
    if s < 60:
        return f"{s:.1f}s"
    m = s / 60
    if m < 60:
        return f"{int(m)}m {int(s % 60)}s"
    h = m / 60
    if h < 24:
        return f"{int(h)}h {int(m % 60)}m"
    d = h / 24
    return f"{int(d)}d {int(h % 24)}h"


def _fmt_ts(ts_str: str | None) -> str:
    """Format ISO timestamp for display in local time."""
    if not ts_str:
        return "—"
    try:
        s = ts_str.replace("Z", "+00:00").replace(" ", "T")
        dt = datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts_str[:19] if len(ts_str) >= 19 else str(ts_str)


def _parse_date_hour(ts_str: str | None) -> str:
    """Parse ISO timestamp into 'YYYY-MM-DD HH:00' bucket key."""
    if not ts_str:
        return "unknown 00:00"
    try:
        s = ts_str.replace("Z", "+00:00").replace(" ", "T")
        dt = datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d %H:00")
    except Exception:
        return "unknown 00:00"


def _parse_date(ts_str: str | None) -> str:
    """Extract YYYY-MM-DD from ISO timestamp."""
    d = _parse_date_hour(ts_str)
    return d[:10] if len(d) >= 10 else d


def _parse_week(ts_str: str | None) -> str:
    """Extract ISO week label like '2026-W25' (matching telemetry server getIsoWeek)."""
    if not ts_str:
        return "unknown"
    try:
        s = ts_str.replace("Z", "+00:00").replace(" ", "T")
        dt = datetime.fromisoformat(s)
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    except Exception:
        return "unknown"


def _parse_month(ts_str: str | None) -> str:
    """Extract YYYY-MM from ISO timestamp."""
    d = _parse_date(ts_str)
    return d[:7] if len(d) >= 7 else d


def _compute_entity_rollup(operations: list[dict]) -> list[dict]:
    """
    Group operations by workflow-id (from metadata) into entities.
    Standalone ops (no workflow-id) get their own entity.
    Returns list of {entity_id, tool_name, command, status, total_duration_ms, start_time, end_time}.
    """
    # Separate workflow ops from standalone
    workflows: dict[str, list[dict]] = {}
    standalones: list[dict] = []

    for op in operations:
        wf_id = (op.get("metadata") or {}).get("workflow-id")
        if wf_id:
            workflows.setdefault(wf_id, []).append(op)
        else:
            standalones.append(op)

    entities = []

    # Workflow entities
    for wf_id, steps in workflows.items():
        steps_sorted = sorted(steps, key=lambda x: x.get("started_at", ""))
        # Determine end-to-end status matching telemetry server SQL:
        #   1. Any step with stage=finalize & status=success → success
        #   2. Most recent step status == failure → failure
        #   3. Most recent step status == success → abandoned
        #   4. Else: most recent step status
        most_recent = steps_sorted[-1] if steps_sorted else {}
        most_recent_status = most_recent.get("status", "unknown")
        has_finalized_success = any(
            (s.get("metadata") or {}).get("stage") == "finalize"
            and s.get("status") == "success"
            for s in steps_sorted
        )
        if has_finalized_success:
            final_status = "success"
        elif most_recent_status == "failure":
            final_status = "failure"
        elif most_recent_status == "success":
            final_status = "abandoned"
        else:
            final_status = most_recent_status

        total_ms = sum(s.get("duration_ms", 0) or 0 for s in steps_sorted)
        entities.append({
            "entity_id": wf_id,
            "tool_name": steps_sorted[0].get("tool_name", "unknown"),
            "command": steps_sorted[0].get("command", "unknown"),
            "status": final_status,
            "total_duration_ms": total_ms,
            "start_time": steps_sorted[0].get("started_at"),
            "end_time": steps_sorted[-1].get("finished_at"),
            "steps": steps_sorted,
            "is_workflow": True,
        })

    # Standalone entities
    for op in standalones:
        entities.append({
            "entity_id": f"std_{op.get('source_file', '')}",
            "tool_name": op.get("tool_name", "unknown"),
            "command": op.get("command", "unknown"),
            "status": op.get("status", "unknown"),
            "total_duration_ms": op.get("duration_ms", 0) or 0,
            "start_time": op.get("started_at"),
            "end_time": op.get("finished_at"),
            "steps": [op],
            "is_workflow": False,
        })

    # Sort newest-first so the log feed shows recent entries at the top
    entities.sort(key=lambda e: e.get("start_time") or "", reverse=True)
    return entities


def _trunc(s: str, max_len: int = 35) -> str:
    """Truncate a string for display in charts."""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "…"


def _format_window_label(window_key: str, view: str) -> str:
    """Format window key for display (matching telemetry server formatWindowLabel).
    
    Hourly → "MM/DD/YYYY", Daily → "Mon YYYY", else → window_key.
    """
    if view == "Hourly":
        parts = window_key.split("-")
        if len(parts) == 3:
            return f"{parts[1]}/{parts[2]}/{parts[0]}"
        return window_key
    if view == "Daily":
        parts = window_key.split("-")
        if len(parts) == 2:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            m_idx = int(parts[1]) - 1
            if 0 <= m_idx < 12:
                return f"{months[m_idx]} {parts[0]}"
        return window_key
    return window_key


def _get_stable_colors(labels: list[str]) -> list[str]:
    """Generate stable colors for a list of tool/command labels.
    
    Uses golden ratio with hash seeding so the same label always gets the same color.
    """
    phi_inv = 0.618033988749895
    colors = []
    for label in labels:
        h = hash(label.lower()) % 360
        hue = (abs(h) * phi_inv * 360) % 360
        colors.append(f"hsl({hue:.0f}, 70%, 55%)")
    return colors


# ──────────────────────────────────────────────────────────────────────
# Page: Mindlayer Skills (adapted from skills-telemetry-server dashboard)
# ──────────────────────────────────────────────────────────────────────

def page_mindlayer_skills():
    st.header("🧠 Mindlayer Skills Telemetry")

    if show_api_error():
        return

    operations = _get_log_payloads()
    if not operations:
        st.info("No log payloads data available. Run the collector to generate data.", icon="ℹ️")
        return

    # ── Filters ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.caption("**Controls**")
        all_tools = sorted(set(op.get("tool_name", "unknown") for op in operations))
        all_cmds = sorted(set(op.get("command", "unknown") for op in operations))
        all_statuses = sorted(set(op.get("status", "unknown") for op in operations))

        f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
        with f1:
            selected_tool = st.selectbox("Tool", ["All"] + all_tools, key="ml_tool")
        with f2:
            selected_command = st.selectbox("Command", ["All"] + all_cmds, key="ml_command")
        with f3:
            selected_status = st.selectbox("Status", ["All"] + all_statuses, key="ml_status")
        with f4:
            st.markdown("<br>", unsafe_allow_html=True)
            clear = st.button("Clear", key="ml_clear", use_container_width=True)
            if clear:
                selected_tool = "All"
                selected_command = "All"
                selected_status = "All"
                st.rerun()

    # Apply filters
    filtered = operations
    if selected_tool != "All":
        filtered = [op for op in filtered if op.get("tool_name") == selected_tool]
    if selected_command != "All":
        filtered = [op for op in filtered if op.get("command") == selected_command]
    if selected_status != "All":
        filtered = [op for op in filtered if op.get("status") == selected_status]

    if not filtered:
        st.warning("No operations match the selected filters.", icon="⚠️")
        return

    # ── Entity rollup (for KPIs + feed) ──
    entities = _compute_entity_rollup(filtered)
    total_executions = len(entities)

    # Status counts
    status_counts: dict[str, int] = {}
    for e in entities:
        s = e["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    STATUS_COLORS = {
        "success": "#10b981", "failure": "#ef4444", "abandoned": "#f59e0b",
        "failed": "#ef4444", "incomplete": "#f59e0b", "unknown": "#94a3b8",
    }
    STATUS_ORDER = ["success", "abandoned", "incomplete", "failure", "failed", "unknown"]

    # ── Row 1: KPI + Status Breakdown (full width) ────────────────────
    st.markdown("### Metrics Dashboard")

    total_for_bar = max(1, sum(status_counts.values()))
    bar_html = '<div style="display:flex;height:12px;border-radius:6px;overflow:hidden;width:100%;background:#e2e8f0;margin-top:4px;">'
    for s in STATUS_ORDER:
        if s in status_counts:
            pct = status_counts[s] / total_for_bar * 100
            color = STATUS_COLORS.get(s, "#94a3b8")
            bar_html += f'<div style="width:{pct:.1f}%;background:{color};" title="{s}: {status_counts[s]} ({pct:.0f}%)"></div>'
    bar_html += '</div>'
    st.metric("Total Executions", total_executions)
    st.html(bar_html)
    # Legend
    legend_parts = []
    for s in STATUS_ORDER:
        if s in status_counts:
            pct = status_counts[s] / total_for_bar * 100
            color = STATUS_COLORS.get(s, "#94a3b8")
            legend_parts.append(
                f'<span style="color:{color};font-weight:600;font-size:0.80rem;">{pct:.0f}% {s.title()}</span>'
            )
    st.html('<div style="margin-top:6px;display:flex;gap:16px;flex-wrap:wrap;">' + " ".join(legend_parts) + '</div>')

    # ── Row 2: Tool Time Usage (doughnut) + Top Commands by Time (bar) ──
    st.divider()
    c1, c2 = st.columns(2)

    # Left: Doughnut — Tool Time Usage
    with c1:
        st.subheader("Tool Time Usage")
        tool_time: dict[str, float] = {}
        for e in entities:
            tn = e["tool_name"]
            tool_time[tn] = tool_time.get(tn, 0) + e["total_duration_ms"]
        if tool_time:
            items = sorted(tool_time.items(), key=lambda x: x[1], reverse=True)
            labels = [_trunc(k) for k, _ in items]
            values = [v for _, v in items]
            colors = _get_stable_colors([k for k, _ in items])
            fig = go.Figure(go.Pie(
                labels=labels, values=values, hole=0.5,
                marker=dict(colors=colors),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>%{value:,.0f}ms<br>%{percent}<extra></extra>",
            ))
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=350,
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02,
                           font=dict(size=10)),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No data")

    # Right: Horizontal Bar — Top Commands by Time
    with c2:
        st.subheader("Top Commands by Time")
        cmd_time: dict[str, float] = {}
        for e in entities:
            cn = e["command"]
            cmd_time[cn] = cmd_time.get(cn, 0) + e["total_duration_ms"]
        if cmd_time:
            items = sorted(cmd_time.items(), key=lambda x: x[1], reverse=True)[:10]
            labels = [_trunc(k) for k, _ in items]
            values = [v / 1000 for _, v in items]  # convert ms → s for axis
            colors = _get_stable_colors([k for k, _ in items])
            fig = go.Figure(go.Bar(
                x=values, y=labels, orientation="h",
                marker_color=colors,
                hovertemplate="<b>%{y}</b><br>%{x:,.1f}s<extra></extra>",
            ))
            fig.update_layout(
                bargap=0.15,
                margin=dict(l=0, r=0, t=0, b=0),
                height=350,
                xaxis_title="Total Time (seconds)",
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No data")

    # ── Row 3: Activity Timeline ──────────────────────────────────────
    st.divider()
    st.markdown("### Activity Timeline")

    # Session state for timeline windowing
    if "ml_timeline_view" not in st.session_state:
        st.session_state.ml_timeline_view = "Daily"
    if "ml_timeline_window_idx" not in st.session_state:
        st.session_state.ml_timeline_window_idx = -1  # -1 means "latest"

    view = st.session_state.ml_timeline_view

    # Resolution buttons (mimic telemetry server)
    res_col, group_col, _ = st.columns([2, 1, 2])
    with res_col:
        btn_h, btn_d, btn_w, btn_m = st.columns(4)
        hourly_style = "primary" if view == "Hourly" else "secondary"
        daily_style = "primary" if view == "Daily" else "secondary"
        weekly_style = "primary" if view == "Weekly" else "secondary"
        monthly_style = "primary" if view == "Monthly" else "secondary"
        with btn_h:
            if st.button("Hourly", key="ml_tl_hourly", type=hourly_style, use_container_width=True):
                st.session_state.ml_timeline_view = "Hourly"
                st.session_state.ml_timeline_window_idx = -1
                st.rerun()
        with btn_d:
            if st.button("Daily", key="ml_tl_daily", type=daily_style, use_container_width=True):
                st.session_state.ml_timeline_view = "Daily"
                st.session_state.ml_timeline_window_idx = -1
                st.rerun()
        with btn_w:
            if st.button("Weekly", key="ml_tl_weekly", type=weekly_style, use_container_width=True):
                st.session_state.ml_timeline_view = "Weekly"
                st.session_state.ml_timeline_window_idx = -1
                st.rerun()
        with btn_m:
            if st.button("Monthly", key="ml_tl_monthly", type=monthly_style, use_container_width=True):
                st.session_state.ml_timeline_view = "Monthly"
                st.session_state.ml_timeline_window_idx = -1
                st.rerun()

    with group_col:
        timeline_grouping = st.selectbox(
            "Group By", ["Tool", "Command"], key="ml_timeline_group"
        )

    # Build timeline data from raw filtered operations
    if view == "Hourly":
        bucket_fn = _parse_date_hour
        window_fn = lambda bk: bk[:10]  # YYYY-MM-DD
    elif view == "Daily":
        bucket_fn = _parse_date
        window_fn = lambda bk: bk[:7]   # YYYY-MM
    elif view == "Weekly":
        bucket_fn = _parse_week
    else:  # Monthly
        bucket_fn = _parse_month

    if view in ("Weekly", "Monthly"):
        window_fn = lambda bk: bk[:4]   # YYYY

    group_key = "tool_name" if timeline_grouping == "Tool" else "command"

    # Aggregate: {bucket_key: {group_name: count}}
    timeline_buckets: dict[str, dict[str, int]] = {}
    for op in filtered:
        bucket = bucket_fn(op.get("started_at"))
        gk = op.get(group_key, "unknown")
        if bucket not in timeline_buckets:
            timeline_buckets[bucket] = {}
        timeline_buckets[bucket][gk] = timeline_buckets[bucket].get(gk, 0) + 1

    if not timeline_buckets:
        st.caption("No timeline data")
    else:
        # Compute windows
        windows = sorted(set(window_fn(bk) for bk in timeline_buckets))

        # Resolve window index
        if st.session_state.ml_timeline_window_idx < 0 or st.session_state.ml_timeline_window_idx >= len(windows):
            st.session_state.ml_timeline_window_idx = len(windows) - 1
        current_window = windows[st.session_state.ml_timeline_window_idx]

        # Filter to current window
        window_buckets = {
            bk: groups for bk, groups in timeline_buckets.items()
            if window_fn(bk) == current_window
        }
        sorted_buckets = sorted(window_buckets.keys())

        # Get top groups within this window
        all_groups: dict[str, int] = {}
        for bk in sorted_buckets:
            for gk, cnt in window_buckets[bk].items():
                all_groups[gk] = all_groups.get(gk, 0) + cnt
        top_groups = [g for g, _ in sorted(all_groups.items(), key=lambda x: x[1], reverse=True)[:8]]

        # Short labels for x-axis (matching telemetry server)
        if view == "Hourly":
            x_labels = [bk[11:16] if len(bk) >= 16 else bk for bk in sorted_buckets]  # "14:00"
        elif view == "Daily":
            x_labels = [bk[8:10] if len(bk) >= 10 else bk for bk in sorted_buckets]  # "18"
        else:
            x_labels = sorted_buckets  # "2026-W25" or "2026-06"

        # Build stacked bar chart
        fig = go.Figure()
        colors = _get_stable_colors(top_groups)
        for i, g in enumerate(top_groups):
            counts = [window_buckets[bk].get(g, 0) for bk in sorted_buckets]
            fig.add_trace(go.Bar(
                name=_trunc(g, 40), x=x_labels, y=counts,
                marker_color=colors[i],
                hovertemplate=f"<b>{g}</b><br>%{{x}}: %{{y}}<extra></extra>",
            ))

        fig.update_layout(
            barmode="stack",
            margin=dict(l=0, r=0, t=0, b=40),
            height=350,
            legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5,
                       font=dict(size=10)),
            xaxis_title="Time Period",
            yaxis_title="Executions",
        )
        fig.update_yaxes(rangemode="tozero")

        # Window navigation (prev/next)
        nav_prev, nav_label, nav_next = st.columns([1, 2, 1])
        with nav_prev:
            prev_disabled = st.session_state.ml_timeline_window_idx <= 0
            if st.button("← Previous", key="ml_tl_prev", disabled=prev_disabled, use_container_width=True):
                if not prev_disabled:
                    st.session_state.ml_timeline_window_idx -= 1
                    st.rerun()
        with nav_label:
            window_display = _format_window_label(current_window, view)
            st.caption(f"Window: {window_display}  ({st.session_state.ml_timeline_window_idx + 1}/{len(windows)})")
        with nav_next:
            next_disabled = st.session_state.ml_timeline_window_idx >= len(windows) - 1
            if st.button("Next →", key="ml_tl_next", disabled=next_disabled, use_container_width=True):
                if not next_disabled:
                    st.session_state.ml_timeline_window_idx += 1
                    st.rerun()

        st.plotly_chart(fig, use_container_width=True)

    # ── Logs Table ────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Logs")

    # Pagination
    PAGE_SIZE = 25
    if "ml_page" not in st.session_state:
        st.session_state.ml_page = 0
    total_pages = max(1, (len(entities) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = st.session_state.ml_page
    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, len(entities))
    page_entities = entities[start_idx:end_idx]

    pag_col1, pag_col2, pag_col3 = st.columns([1, 2, 1])
    with pag_col1:
        if st.button("← Previous Page", key="ml_feed_prev", disabled=page <= 0, use_container_width=True):
            st.session_state.ml_page = page - 1
            st.rerun()
    with pag_col2:
        st.caption(f"Page {page + 1} of {total_pages}  ({start_idx + 1}–{end_idx} of {len(entities)})")
    with pag_col3:
        if st.button("Next Page →", key="ml_feed_next", disabled=page >= total_pages - 1, use_container_width=True):
            st.session_state.ml_page = page + 1
            st.rerun()

    # Render each entity as an expandable card
    for entity in page_entities:
        eid = entity["entity_id"]
        is_wf = entity["is_workflow"]
        status = entity["status"]
        status_color = STATUS_COLORS.get(status, "#94a3b8")
        duration_str = _fmt_duration(entity["total_duration_ms"])

        with st.container(border=True):
            # Header row
            h1, h2, h3, h4, h5 = st.columns([2, 1, 1, 1, 0.8])
            with h1:
                badge = "🔗" if is_wf else "📋"
                st.markdown(
                    f"{badge} **{_trunc(entity['tool_name'])}** · `{_trunc(entity['command'])}`  "
                    f"<span style='color:{status_color};font-weight:600;'>● {status.upper()}</span>",
                    unsafe_allow_html=True,
                )
            with h2:
                st.caption(f"Duration: {duration_str}")
            with h3:
                st.caption(f"Started: {_fmt_ts(entity['start_time'])}")
            with h4:
                st.caption(f"Entity: `{_trunc(eid, 28)}`")
            with h5:
                expand_key = f"ml_expand_{eid}"
                if st.button("Details", key=f"ml_btn_{eid}"):
                    st.session_state[expand_key] = not st.session_state.get(expand_key, False)

            # Expandable detail drawer
            if st.session_state.get(expand_key, False):
                st.divider()
                for step in entity["steps"]:
                    step_status = step.get("status", "unknown")
                    sc = STATUS_COLORS.get(step_status, "#94a3b8")
                    with st.container(border=True):
                        sd1, sd2, sd3 = st.columns([2, 1, 1])
                        with sd1:
                            st.markdown(
                                f"**{_trunc(step.get('command', '?'))}**  "
                                f"<span style='color:{sc};font-weight:600;'>● {step_status}</span>",
                                unsafe_allow_html=True,
                            )
                        with sd2:
                            st.caption(f"Duration: {_fmt_duration(step.get('duration_ms'))}")
                        with sd3:
                            stage = (step.get("metadata") or {}).get("stage", "")
                            st.caption(f"Stage: {stage or '—'}")

                        # Input flags
                        flags = step.get("input_flags") or {}
                        if flags:
                            flag_str = "  ".join(
                                f"`--{k}`: **{str(v)[:80]}**" for k, v in list(flags.items())[:6]
                            )
                            st.caption(flag_str)
                            if len(flags) > 6:
                                st.caption(f"…and {len(flags) - 6} more flags")

                        # Error
                        error = step.get("error")
                        if error:
                            st.error(str(error)[:500])

                        # Result size
                        rs = step.get("result_size")
                        if rs:
                            st.caption(f"Result size: {rs:,} bytes")

                        # Source file
                        sf = step.get("source_file", "")
                        if sf:
                            st.caption(f"Source: `{sf}`")



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

mindlayer_skills_page = st.Page(
    page_mindlayer_skills, title="Mindlayer Skills", icon="🧠", url_path="mindlayer_skills"
)

nav = st.navigation(
    {"Main": [portal_page, overview_page, detail_page, skills_page, tools_page, mindlayer_skills_page]}
)

# ── Sidebar: Shutdown button ──
with st.sidebar:
    st.markdown("---")
    if st.button("🛑 Shutdown Analytics", type="primary", use_container_width=True):
        shutdown_analytics()

nav.run()
