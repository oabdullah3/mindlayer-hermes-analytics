#!/usr/bin/env python3
"""
Hermes Analytics — CLI Metrics Renderer

Reads snapshot_latest.json and prints a formatted terminal summary
of Mindlayer Skills telemetry. No browser, no server, no dependencies
beyond Python stdlib.

Designed for:
  - hermes snapshot-analytics --mode cli     (explicit)
  - hermes snapshot-analytics                (default = cli)
  - /hermes-snapshot-analytics --mode cli
  - /hermes-snapshot-analytics                (default = cli)
  - --fallback (auto-switch if browser mode fails)
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


# ──────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────

def load_snapshot(path: str = "snapshot_latest.json") -> dict | None:
    """Load snapshot JSON from disk. Returns None if file missing."""
    # Try common locations
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
    """Format milliseconds to human-readable string."""
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


def _fmt_ts(ts_str: str | None, short: bool = False) -> str:
    """Format ISO timestamp for display."""
    if not ts_str:
        return "—"
    try:
        s = ts_str.replace("Z", "+00:00").replace(" ", "T")
        dt = datetime.fromisoformat(s)
        if short:
            return dt.strftime("%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts_str[:19] if len(ts_str) >= 19 else str(ts_str)


def _trunc(s: str, max_len: int = 30) -> str:
    """Truncate a string for display."""
    if len(s) <= max_len:
        return s
    return s[:max_len - 1] + "…"


def _fmt_pct(value: float, total: float) -> str:
    """Format a percentage string."""
    if total == 0:
        return "  0.0%"
    pct = value / total * 100
    return f"{pct:5.1f}%"


# ──────────────────────────────────────────────────────────────────────
# Bar chart (ASCII sparkline)
# ──────────────────────────────────────────────────────────────────────

def _ascii_bar(value: float, max_value: float, width: int = 30) -> str:
    """Render a proportional ASCII bar using block characters."""
    if max_value == 0:
        return "▏" + " " * (width - 1)
    filled = int(value / max_value * width)
    if filled == 0 and value > 0:
        return "▏" + " " * (width - 1)
    return "█" * filled + " " * (width - filled)


def _status_sparkline(status_counts: dict[str, int], width: int = 40) -> str:
    """Render a colored status breakdown as a proportional bar.
    
    We use Unicode block characters annotated with status labels.
    Color is not portable across all terminals, so we use symbolic markers.
    """
    total = max(1, sum(status_counts.values()))
    chars: list[str] = []
    order = ["success", "abandoned", "incomplete", "failure", "failed", "unknown"]
    markers = {"success": "▓", "failure": "▓", "failed": "▓", "abandoned": "▒", "incomplete": "░", "unknown": " "}
    for s in order:
        if s in status_counts:
            n = max(1, int(status_counts[s] / total * width))
            chars.append(markers.get(s, " ") * n)
    return "".join(chars)


# ──────────────────────────────────────────────────────────────────────
# Entity rollup (matching dashboard.py logic)
# ──────────────────────────────────────────────────────────────────────

def _compute_entity_rollup(operations: list[dict]) -> list[dict]:
    """Group by workflow-id, resolve status, compute durations."""
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

    return entities


# ──────────────────────────────────────────────────────────────────────
# Section renderers
# ──────────────────────────────────────────────────────────────────────

def _print_header(snapshot: dict) -> None:
    """Print the top banner."""
    generated = snapshot.get("generated_at", "unknown")
    try:
        ts = generated.replace("Z", "+00:00").replace(" ", "T")
        dt = datetime.fromisoformat(ts)
        pretty_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        pretty_time = str(generated)

    print()
    print("╔" + "═" * 64 + "╗")
    print("║" + "  🧠  HERMES ANALYTICS — MINDLAYER SKILLS TELEMETRY".ljust(61) + "║")
    print("║" + f"  Snapshot: {pretty_time}".ljust(61) + "║")
    print("╚" + "═" * 64 + "╝")
    print()


def _print_metrics(operations: list[dict]) -> None:
    """KPI row: total executions + status breakdown + bar."""
    entities = _compute_entity_rollup(operations)
    total = len(entities)

    # Status counts
    status_counts: dict[str, int] = {}
    for e in entities:
        s = e["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    print("┌─ 📊 METRICS DASHBOARD " + "─" * 43 + "┐")
    print(f"│  Total Executions:  {total:<5}                             │")

    # Status breakdown with ASCII bar
    total_for_bar = max(1, sum(status_counts.values()))
    bar = _status_sparkline(status_counts, width=40)
    print(f"│  Status:  {bar} │")

    # Percentage breakdown
    parts: list[str] = []
    for s in ["success", "abandoned", "incomplete", "failure", "failed", "unknown"]:
        if s in status_counts:
            pct = status_counts[s] / total_for_bar * 100
            parts.append(f"{s}={status_counts[s]}({pct:.0f}%)")
    print(f"│  Breakdown:  {', '.join(parts)}".ljust(67) + "│")
    print("└" + "─" * 64 + "┘")
    print()


def _print_tool_usage(operations: list[dict]) -> None:
    """Tool Time Usage table."""
    entities = _compute_entity_rollup(operations)
    tool_time: dict[str, float] = {}
    tool_count: dict[str, int] = {}
    for e in entities:
        tn = e["tool_name"]
        tool_time[tn] = tool_time.get(tn, 0) + e["total_duration_ms"]
        tool_count[tn] = tool_count.get(tn, 0) + 1

    if not tool_time:
        print("No tool data.")
        return

    total_ms = sum(tool_time.values())
    items = sorted(tool_time.items(), key=lambda x: x[1], reverse=True)

    print("┌─ 🛠️  TOOL TIME USAGE " + "─" * 44 + "┐")
    print(f"│ {'Tool':<26s} {'Duration':>10s} {'%':>7s} {'Count':>7s}   │")
    print("│" + "─" * 62 + "│")
    for tool, dur in items:
        pct = _fmt_pct(dur, total_ms)
        cnt = tool_count[tool]
        print(f"│ {_trunc(tool, 25):<26s} {_fmt_duration(int(dur)):>10s} {pct:>7s} {cnt:>7d}   │")
    print("└" + "─" * 64 + "┘")
    print()


def _print_top_commands(operations: list[dict]) -> None:
    """Top Commands by Time table."""
    entities = _compute_entity_rollup(operations)
    cmd_time: dict[str, float] = {}
    cmd_count: dict[str, int] = {}
    for e in entities:
        cn = e["command"]
        cmd_time[cn] = cmd_time.get(cn, 0) + e["total_duration_ms"]
        cmd_count[cn] = cmd_count.get(cn, 0) + 1

    if not cmd_time:
        print("No command data.")
        return

    total_ms = sum(cmd_time.values())
    items = sorted(cmd_time.items(), key=lambda x: x[1], reverse=True)[:10]

    print("┌─ 📋 TOP COMMANDS BY TIME " + "─" * 40 + "┐")
    print(f"│ {'Command':<26s} {'Duration':>10s} {'%':>7s} {'Count':>7s}   │")
    print("│" + "─" * 62 + "│")
    for cmd, dur in items:
        pct = _fmt_pct(dur, total_ms)
        cnt = cmd_count[cmd]
        print(f"│ {_trunc(cmd, 25):<26s} {_fmt_duration(int(dur)):>10s} {pct:>7s} {cnt:>7d}   │")
    print("└" + "─" * 64 + "┘")
    print()


def _print_timeline(operations: list[dict]) -> None:
    """Daily activity timeline (last 14 days, ASCII sparkline)."""
    from collections import defaultdict

    daily: dict[str, int] = defaultdict(int)
    for op in operations:
        ts = op.get("started_at", "")
        try:
            s = ts.replace("Z", "+00:00").replace(" ", "T")
            dt = datetime.fromisoformat(s)
            day = dt.strftime("%Y-%m-%d")
            daily[day] += 1
        except Exception:
            pass

    if not daily:
        print("No timeline data.")
        return

    sorted_days = sorted(daily.keys())[-14:]  # last 14 days
    max_count = max(daily.values())

    print("┌─ 📈 ACTIVITY TIMELINE (last 14 days) " + "─" * 30 + "┐")
    for day in sorted_days:
        count = daily[day]
        bar = _ascii_bar(count, max_count, width=25)
        print(f"│ {day}  {bar} {count:>4d}  │")
    print("└" + "─" * 64 + "┘")
    print()


def _print_recent_logs(operations: list[dict], limit: int = 15) -> None:
    """Recent log entries table."""
    # Sort by started_at descending, take most recent
    sorted_ops = sorted(
        operations,
        key=lambda x: x.get("started_at") or "",
        reverse=True,
    )[:limit]

    if not sorted_ops:
        print("No log entries.")
        return

    status_markers = {
        "success": "✓", "failure": "✗", "failed": "✗",
        "abandoned": "◌", "incomplete": "◌", "unknown": "?",
    }

    print("┌─ 📋 RECENT LOGS " + "─" * 47 + "┐")
    print(f"│ {'St':>2s} {'Tool':<18s} {'Command':<14s} {'Duration':>8s} {'Started':>14s}  │")
    print("│" + "─" * 62 + "│")
    for op in sorted_ops:
        status = op.get("status", "?")
        marker = status_markers.get(status, "?")
        tool = _trunc(op.get("tool_name", "?"), 17)
        cmd = _trunc(op.get("command", "?"), 13)
        dur = _fmt_duration(op.get("duration_ms"))
        ts = _fmt_ts(op.get("started_at"), short=True)
        print(f"│ {marker:>2s} {tool:<18s} {cmd:<14s} {dur:>8s} {ts:>14s}  │")
    print("└" + "─" + "─" * 62 + "┘")
    print()


def _print_footer() -> None:
    """Print footer with helpful info."""
    print("─" * 66)
    print("💡 Tips:")
    print("   hermes snapshot-analytics --mode browser    → Open interactive dashboard")
    print("   hermes snapshot-analytics --mode both       → CLI output + browser")
    print("   hermes snapshot-analytics --fallback        → Auto-switch on failure")
    print()


# ──────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────

def render_cli(snapshot_path: str | None = None) -> str | None:
    """Render the full CLI output. Returns None on success, error string on failure.

    Call this from the plugin handler — it prints directly to stdout.
    Use snapshot_path=None to auto-discover snapshot_latest.json.
    """
    snap = load_snapshot(snapshot_path) if snapshot_path else load_snapshot()
    if not snap:
        return (
            "❌ No snapshot data found.\n"
            "Run the collector first:\n"
            "   python3 collector.py\n"
            "Or use --mode browser to start the full analytics pipeline."
        )

    operations = snap.get("log_payloads", {}).get("operations", [])
    if not operations:
        return (
            "⚠️  Snapshot loaded but contains no log payload operations.\n"
            "The collector may have run without generating any log data."
        )

    _print_header(snap)
    _print_metrics(operations)
    _print_tool_usage(operations)
    _print_top_commands(operations)
    _print_timeline(operations)
    _print_recent_logs(operations)
    _print_footer()

    return None  # success


if __name__ == "__main__":
    # Standalone test: python3 cli_metrics.py
    err = render_cli()
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)
