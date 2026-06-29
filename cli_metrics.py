#!/usr/bin/env python3
"""
Hermes Analytics — CLI Metrics Renderer

Reads snapshot_latest.json and prints a formatted terminal summary covering
everything the Streamlit dashboard shows: sessions, skills, tools, tokens,
shell commands, and Mindlayer Skills log-payload telemetry.  No browser,
no server, no dependencies beyond Python stdlib.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone


# ──────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────

def load_snapshot(path: str = "snapshot_latest.json") -> dict | None:
    candidates = [
        path,
        os.path.join(os.path.dirname(__file__), path),
        os.path.join(os.getcwd(), path),
    ]
    for p in candidates:
        if os.path.isfile(p):
            with open(p) as f:
                return json.load(f)
    return None


# ──────────────────────────────────────────────────────────────────────
# Formatters
# ──────────────────────────────────────────────────────────────────────

def _fmt_duration(ms: int | None) -> str:
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
    return f"{int(h / 24)}d {int(h % 24)}h"


def _fmt_ts(ts_val, short: bool = False) -> str:
    if not ts_val:
        return "—"
    try:
        if isinstance(ts_val, (int, float)):
            dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
        return dt.strftime("%m-%d %H:%M") if short else dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        s = str(ts_val)
        return s[:16] if len(s) >= 16 else s


def _trunc(s: str, max_len: int = 30) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len - 1] + "…"


def _fmt_pct(value: float, total: float) -> str:
    if total == 0:
        return "  0.0%"
    return f"{value / total * 100:5.1f}%"


def _ascii_bar(value: float, max_value: float, width: int = 30) -> str:
    if max_value == 0:
        return "▏" + " " * (width - 1)
    filled = int(value / max_value * width)
    if filled == 0 and value > 0:
        return "▏" + " " * (width - 1)
    return "█" * filled + " " * (width - filled)


def _box_top(title: str, width: int = 66) -> None:
    print(f"┌─ {title} " + "─" * (width - len(title) - 4) + "┐")


def _box_bottom(width: int = 66) -> None:
    print("└" + "─" * width + "┘")


def _sep() -> None:
    print("│" + "─" * 66 + "│")


# ──────────────────────────────────────────────────────────────────────
# Token helpers
# ──────────────────────────────────────────────────────────────────────

def _total_tokens(sessions: list[dict]) -> dict[str, int]:
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "reasoning": 0}
    for s in sessions:
        t = s.get("tokens", {})
        for k in totals:
            totals[k] += int(t.get(k, 0) or 0)
    return totals


# ──────────────────────────────────────────────────────────────────────
# Session duration
# ──────────────────────────────────────────────────────────────────────

def _session_duration(s: dict) -> str:
    started = s.get("started_at")
    ended = s.get("ended_at")
    if not started or not ended:
        return "—"
    try:
        if isinstance(started, (int, float)):
            start_dt = datetime.fromtimestamp(started, tz=timezone.utc)
        else:
            start_dt = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        if isinstance(ended, (int, float)):
            end_dt = datetime.fromtimestamp(ended, tz=timezone.utc)
        else:
            end_dt = datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
        delta = (end_dt - start_dt).total_seconds()
        if delta < 0:
            return "—"
        return _fmt_duration(int(delta * 1000))
    except Exception:
        return "—"


# ──────────────────────────────────────────────────────────────────────
# Entity rollup (for log_payloads)
# ──────────────────────────────────────────────────────────────────────

def _compute_entity_rollup(operations: list[dict]) -> list[dict]:
    workflows: dict[str, list[dict]] = {}
    standalones: list[dict] = []
    for op in operations:
        wf_id = (op.get("metadata") or {}).get("workflow-id")
        if wf_id:
            workflows.setdefault(wf_id, []).append(op)
        else:
            standalones.append(op)
    entities: list[dict] = []
    for wf_id, steps in workflows.items():
        steps_sorted = sorted(steps, key=lambda x: x.get("started_at", ""))
        most_recent = steps_sorted[-1]
        status = most_recent.get("status", "unknown")
        if any((s.get("metadata") or {}).get("stage") == "finalize" and s.get("status") == "success" for s in steps_sorted):
            final_status = "success"
        elif status == "failure":
            final_status = "failure"
        elif status == "success":
            final_status = "abandoned"
        else:
            final_status = status
        total_ms = sum(s.get("duration_ms", 0) or 0 for s in steps_sorted)
        entities.append({
            "entity_id": wf_id, "tool_name": steps_sorted[0].get("tool_name", "unknown"),
            "command": steps_sorted[0].get("command", "unknown"), "status": final_status,
            "total_duration_ms": total_ms, "start_time": steps_sorted[0].get("started_at"),
            "end_time": steps_sorted[-1].get("finished_at"),
            "steps": steps_sorted, "is_workflow": True,
        })
    for op in standalones:
        entities.append({
            "entity_id": f"std_{op.get('source_file', '')}",
            "tool_name": op.get("tool_name", "unknown"), "command": op.get("command", "unknown"),
            "status": op.get("status", "unknown"), "total_duration_ms": op.get("duration_ms", 0) or 0,
            "start_time": op.get("started_at"), "end_time": op.get("finished_at"),
            "steps": [op], "is_workflow": False,
        })
    return entities


# ══════════════════════════════════════════════════════════════════════
# SECTION: Header
# ══════════════════════════════════════════════════════════════════════

def _print_header(snapshot: dict) -> None:
    generated = _fmt_ts(snapshot.get("generated_at", ""))
    print()
    print("╔" + "═" * 64 + "╗")
    print("║" + "  📊  HERMES ANALYTICS".ljust(65) + "║")
    print("║" + f"  Snapshot: {generated}".ljust(65) + "║")
    print("╚" + "═" * 64 + "╝")
    print()


# ══════════════════════════════════════════════════════════════════════
# SECTION: Session Summary
# ══════════════════════════════════════════════════════════════════════

def _print_session_summary(sessions: list[dict]) -> None:
    if not sessions:
        print("No sessions found.")
        return

    total = len(sessions)
    total_msgs = sum(s.get("stats", {}).get("message_count", 0) for s in sessions)
    total_skill_loads = sum(len(s.get("skills_loaded", [])) for s in sessions)
    total_tool_calls = sum(sum(t.get("count", 0) for t in s.get("tool_calls", [])) for s in sessions)
    models = sorted(set(s.get("model") or "?" for s in sessions))
    platforms = sorted(set(s.get("platform") or "?" for s in sessions))

    _box_top("📋 SESSIONS")
    print(f"│  Total: {total:<5}    Messages: {total_msgs:<8,}    Skill Loads: {total_skill_loads:<5}    Tool Calls: {total_tool_calls:<6,}  │")
    if models:
        print(f"│  Models: {', '.join(models[:5])}{' …' if len(models) > 5 else ''}".ljust(67) + "│")
    if platforms:
        print(f"│  Platforms: {', '.join(platforms)}".ljust(67) + "│")
    _box_bottom()
    print()


# ══════════════════════════════════════════════════════════════════════
# SECTION: Token Usage
# ══════════════════════════════════════════════════════════════════════

def _print_tokens(sessions: list[dict]) -> None:
    t = _total_tokens(sessions)
    total = sum(t.values())
    if total == 0:
        return  # no token data, skip section entirely

    _box_top("🔢 TOKEN USAGE")
    print(f"│  Input: {t['input']:>12,}    Output: {t['output']:>11,}    Cache Read: {t['cache_read']:>9,}  │")
    print(f"│  Cache Write: {t['cache_write']:>6,}    Reasoning: {t['reasoning']:>8,}    Total: {total:>14,}  │")
    _box_bottom()
    print()


# ══════════════════════════════════════════════════════════════════════
# SECTION: Skills Leaderboard
# ══════════════════════════════════════════════════════════════════════

def _print_skills(sessions: list[dict], insights: dict) -> None:
    # Prefer global_insights, fall back to per-session computation
    skills_list = insights.get("skills", [])
    if not skills_list:
        skill_counts: dict[str, dict] = {}
        for s in sessions:
            for sl in s.get("skills_loaded", []):
                name = sl.get("skill_name", "?")
                if name not in skill_counts:
                    skill_counts[name] = {"name": name, "load_count": 0, "token_estimate": 0}
                skill_counts[name]["load_count"] += 1
                skill_counts[name]["token_estimate"] += sl.get("token_estimate", 0) or 0
        skills_list = sorted(skill_counts.values(), key=lambda x: x["load_count"], reverse=True)

    if not skills_list:
        return

    top = skills_list[:10]
    _box_top("⭐ SKILLS LEADERBOARD")
    print(f"│ {'Skill':<30s} {'Loads':>7s} {'Tokens':>10s} {'Bar':>12s} │")
    _sep()
    max_loads = max(sk["load_count"] for sk in top) if top else 1
    for sk in top:
        name = _trunc(sk.get("name") or sk.get("skill_name", "?"), 29)
        loads = sk.get("load_count", 0)
        tokens = sk.get("token_estimate", 0)
        bar = _ascii_bar(loads, max_loads, 12)
        print(f"│ {name:<30s} {loads:>7d} {tokens:>10,d} {bar:>12s} │")
    _box_bottom()
    print()


# ══════════════════════════════════════════════════════════════════════
# SECTION: Tools Leaderboard
# ══════════════════════════════════════════════════════════════════════

def _print_tools(insights: dict) -> None:
    tools_list = insights.get("tools", [])
    if not tools_list:
        return

    top = tools_list[:10]
    _box_top("🔧 TOOLS LEADERBOARD")
    print(f"│ {'Tool':<37s} {'Calls':>7s} {'Bar':>16s} │")
    _sep()
    max_calls = max(t["count"] for t in top) if top else 1
    for t in top:
        name = _trunc(t["name"], 36)
        count = t["count"]
        bar = _ascii_bar(count, max_calls, 16)
        print(f"│ {name:<37s} {count:>7d} {bar:>16s} │")
    _box_bottom()
    print()


# ══════════════════════════════════════════════════════════════════════
# SECTION: Shell Commands
# ══════════════════════════════════════════════════════════════════════

def _print_commands(insights: dict) -> None:
    cmds = insights.get("commands", {})
    most = cmds.get("most_executed_commands", [])
    total = cmds.get("total_commands", 0)
    failed = cmds.get("failed_commands", 0)

    if not most and total == 0:
        return

    _box_top("💻 SHELL COMMANDS")
    print(f"│  Total: {total:<8}    Failed: {failed:<8}".ljust(67) + "│")
    if most:
        _sep()
        print(f"│ {'Command':<40s} {'Count':>7s} {'Bar':>14s} │")
        _sep()
        max_count = max(m["count"] for m in most[:10]) if most else 1
        for cmd in most[:10]:
            name = _trunc(cmd["command"], 39)
            count = cmd["count"]
            bar = _ascii_bar(count, max_count, 14)
            print(f"│ {name:<40s} {count:>7d} {bar:>14s} │")
    _box_bottom()
    print()


# ══════════════════════════════════════════════════════════════════════
# SECTION: Recent Sessions
# ══════════════════════════════════════════════════════════════════════

def _print_recent_sessions(sessions: list[dict]) -> None:
    if not sessions:
        return

    recent = sorted(sessions, key=lambda s: s.get("started_at") or 0, reverse=True)[:10]

    _box_top("📋 RECENT SESSIONS")
    print(f"│ {'Title':<24s} {'Model':<18s} {'Skills':>6s} {'Tools':>5s} {'Tokens':>8s} │")
    _sep()
    for s in recent:
        title = _trunc(s.get("chat_name") or f"#{s.get('session_id','?')}", 23)
        model = _trunc(str(s.get("model") or "?"), 17)
        skills = str(len(s.get("skills_loaded", [])))
        tools = str(sum(t.get("count", 0) for t in s.get("tool_calls", [])))
        tokens = sum(int(v or 0) for v in s.get("tokens", {}).values())
        print(f"│ {title:<24s} {model:<18s} {skills:>6s} {tools:>5s} {tokens:>8,d} │")
    _box_bottom()
    print()


# ══════════════════════════════════════════════════════════════════════
# SECTION: Mindlayer Skills (log payloads)
# ══════════════════════════════════════════════════════════════════════

def _print_ml_metrics(operations: list[dict]) -> None:
    entities = _compute_entity_rollup(operations)
    total = len(entities)
    status_counts: dict[str, int] = {}
    for e in entities:
        s = e["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    _box_top("🧠 MINDLAYER SKILLS — METRICS")
    print(f"│  Total Executions: {total:<5}".ljust(67) + "│")
    bar = _status_sparkline(status_counts, width=40)
    print(f"│  Status:  {bar} │")
    parts = []
    for s in ["success", "abandoned", "incomplete", "failure", "failed", "unknown"]:
        if s in status_counts:
            pct = status_counts[s] / max(1, total) * 100
            parts.append(f"{s}={status_counts[s]}({pct:.0f}%)")
    print(f"│  Breakdown:  {', '.join(parts)}".ljust(67) + "│")
    _box_bottom()
    print()


def _status_sparkline(status_counts: dict[str, int], width: int = 40) -> str:
    total = max(1, sum(status_counts.values()))
    chars: list[str] = []
    order = ["success", "abandoned", "incomplete", "failure", "failed", "unknown"]
    markers = {"success": "▓", "failure": "▓", "failed": "▓", "abandoned": "▒", "incomplete": "░", "unknown": " "}
    for s in order:
        if s in status_counts:
            n = max(1, int(status_counts[s] / total * width))
            chars.append(markers.get(s, " ") * n)
    return "".join(chars)


def _print_ml_tool_usage(operations: list[dict]) -> None:
    entities = _compute_entity_rollup(operations)
    tool_time: dict[str, float] = {}
    tool_count: dict[str, int] = {}
    for e in entities:
        tn = e["tool_name"]
        tool_time[tn] = tool_time.get(tn, 0) + e["total_duration_ms"]
        tool_count[tn] = tool_count.get(tn, 0) + 1
    if not tool_time:
        return

    total_ms = sum(tool_time.values())
    items = sorted(tool_time.items(), key=lambda x: x[1], reverse=True)[:10]
    _box_top("🛠️  TOOL TIME USAGE")
    print(f"│ {'Tool':<26s} {'Duration':>10s} {'%':>7s} {'Count':>7s}   │")
    _sep()
    for tool, dur in items:
        pct = _fmt_pct(dur, total_ms)
        cnt = tool_count[tool]
        print(f"│ {_trunc(tool, 25):<26s} {_fmt_duration(int(dur)):>10s} {pct:>7s} {cnt:>7d}   │")
    _box_bottom()
    print()


def _print_ml_top_commands(operations: list[dict]) -> None:
    entities = _compute_entity_rollup(operations)
    cmd_time: dict[str, float] = {}
    cmd_count: dict[str, int] = {}
    for e in entities:
        cn = e["command"]
        cmd_time[cn] = cmd_time.get(cn, 0) + e["total_duration_ms"]
        cmd_count[cn] = cmd_count.get(cn, 0) + 1
    if not cmd_time:
        return

    total_ms = sum(cmd_time.values())
    items = sorted(cmd_time.items(), key=lambda x: x[1], reverse=True)[:10]
    _box_top("📋 TOP COMMANDS BY TIME")
    print(f"│ {'Command':<26s} {'Duration':>10s} {'%':>7s} {'Count':>7s}   │")
    _sep()
    for cmd, dur in items:
        pct = _fmt_pct(dur, total_ms)
        cnt = cmd_count[cmd]
        print(f"│ {_trunc(cmd, 25):<26s} {_fmt_duration(int(dur)):>10s} {pct:>7s} {cnt:>7d}   │")
    _box_bottom()
    print()


def _print_ml_timeline(operations: list[dict]) -> None:
    daily: dict[str, int] = defaultdict(int)
    for op in operations:
        ts = op.get("started_at", "")
        try:
            dt = None
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            daily[dt.strftime("%Y-%m-%d")] += 1
        except Exception:
            pass
    if not daily:
        return

    sorted_days = sorted(daily.keys())[-14:]
    max_count = max(daily.values())
    _box_top("📈 ACTIVITY TIMELINE (last 14 days)")
    for day in sorted_days:
        count = daily[day]
        bar = _ascii_bar(count, max_count, width=25)
        print(f"│ {day}  {bar} {count:>4d}  │")
    _box_bottom()
    print()


def _print_ml_recent_logs(operations: list[dict], limit: int = 10) -> None:
    sorted_ops = sorted(operations, key=lambda x: x.get("started_at") or "", reverse=True)[:limit]
    if not sorted_ops:
        return

    markers = {"success": "✓", "failure": "✗", "failed": "✗", "abandoned": "◌", "incomplete": "◌", "unknown": "?"}
    _box_top("📋 RECENT LOGS")
    print(f"│ {'St':>2s} {'Tool':<18s} {'Command':<14s} {'Duration':>8s} {'Started':>14s}  │")
    _sep()
    for op in sorted_ops:
        status = op.get("status", "?")
        marker = markers.get(status, "?")
        tool = _trunc(op.get("tool_name", "?"), 17)
        cmd = _trunc(op.get("command", "?"), 13)
        dur = _fmt_duration(op.get("duration_ms"))
        ts = _fmt_ts(op.get("started_at"), short=True)
        print(f"│ {marker:>2s} {tool:<18s} {cmd:<14s} {dur:>8s} {ts:>14s}  │")
    _box_bottom()
    print()


# ──────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────

def _print_footer() -> None:
    print("─" * 68)
    print("💡 Tips:")
    print("   hermes snapshot-analytics --mode browser  → Interactive Streamlit dashboard")
    print("   hermes snapshot-analytics --mode both     → CLI output + browser")
    print()




# ══════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════

def render_cli(snapshot_path: str | None = None) -> str | None:
    """Render the full CLI output.  Returns None on success, error string on failure."""
    snap = load_snapshot(snapshot_path) if snapshot_path else load_snapshot()
    if not snap:
        return (
            "❌ No snapshot data found.\n"
            "Run the collector first:\n"
            "   python3 collector.py\n"
            "Or use --mode browser to start the full analytics pipeline."
        )

    sessions = snap.get("sessions", [])
    insights = snap.get("global_insights", {})
    log_payloads = snap.get("log_payloads", {})
    operations = log_payloads.get("operations", [])
    has_ml = log_payloads.get("available", False) and operations

    if not sessions and not has_ml:
        return "⚠️  Snapshot loaded but contains no sessions or log-payload data."

    # ── Render all sections ──
    _print_header(snap)
    _print_session_summary(sessions)
    _print_tokens(sessions)
    _print_skills(sessions, insights)
    _print_tools(insights)
    _print_commands(insights)
    _print_recent_sessions(sessions)

    if has_ml:
        print("─" * 68)
        print("  🧠  MINDLAYER SKILLS TELEMETRY")
        print("─" * 68)
        print()
        _print_ml_metrics(operations)
        _print_ml_tool_usage(operations)
        _print_ml_top_commands(operations)
        _print_ml_timeline(operations)
        _print_ml_recent_logs(operations)

    _print_footer()
    return None


if __name__ == "__main__":
    err = render_cli()
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)
