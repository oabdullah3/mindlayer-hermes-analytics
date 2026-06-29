#!/usr/bin/env python3
"""
Hermes Analytics — CLI Metrics Renderer

Reads snapshot_latest.json and prints formatted terminal summaries.
- No flags  → compact general overview (hints for drill-down)
- --sessions|--skills|--tools|--tokens|--commands|--mindlayer → detail view

Width-safe: every line inside a box is exactly WIDTH chars.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

WIDTH = 78          # outer box width (consistent everywhere)
INNER = WIDTH - 2   # content area between │...│
TOP_N = 5           # show at most top N in any ranking

# ──────────────────────────────────────────────────────────────────────
# Box-drawing primitives — guarantee exact WIDTH on every line
# ──────────────────────────────────────────────────────────────────────

def _row(text: str) -> str:
    """Return '│' + text padded to INNER chars + '│'.  Always exactly WIDTH."""
    if len(text) > INNER:
        text = text[:INNER - 1] + "…"
    return "│" + text.ljust(INNER) + "│"


def _hline() -> str:
    """Horizontal rule between header and body rows."""
    return "│" + "─" * INNER + "│"


def _top(title: str) -> str:
    """Box top border with embedded title."""
    prefix = f"┌─ {title} "
    dash_count = WIDTH - len(prefix) - 1
    return prefix + "─" * max(0, dash_count) + "┐"


def _bot() -> str:
    """Box bottom border."""
    return "└" + "─" * (WIDTH - 2) + "┘"


def _banner(text: str) -> str:
    """Double-line top banner."""
    return f"╔{'═' * INNER}╗\n║{text.center(INNER)}║\n╚{'═' * INNER}╝"


def _hint(flag: str) -> str:
    """Return a dim hint line pointing to a detail flag."""
    return f"Run with --{flag} for full details"


# ──────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────

def load_snapshot(path: str = "snapshot_latest.json") -> dict | None:
    candidates = [path,
                  os.path.join(os.path.dirname(__file__), path),
                  os.path.join(os.getcwd(), path)]
    for p in candidates:
        if os.path.isfile(p):
            with open(p) as f:
                return json.load(f)
    return None


# ──────────────────────────────────────────────────────────────────────
# Compact number formatting (3.2M, 145K, etc.)
# ──────────────────────────────────────────────────────────────────────

def _num(n: int) -> str:
    """Human-readable compact number: 1234567 → 1.2M"""
    if abs(n) < 1000:
        return str(n)
    if abs(n) < 1_000_000:
        return f"{n / 1000:.1f}K".rstrip("0").rstrip(".")
    if abs(n) < 1_000_000_000:
        return f"{n / 1_000_000:.1f}M".rstrip("0").rstrip(".")
    return f"{n / 1_000_000_000:.1f}B".rstrip("0").rstrip(".")


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
        return f"{int(m)}m{int(s % 60)}s"
    h = m / 60
    if h < 24:
        return f"{int(h)}h{int(m % 60)}m"
    return f"{int(h / 24)}d{int(h % 24)}h"


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


def _trunc(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len - 1] + "…"


def _pct(value: float, total: float) -> str:
    if total == 0:
        return " 0%"
    return f"{value / total * 100:3.0f}%"


def _bar(value: float, max_value: float, width: int = 10) -> str:
    if max_value == 0:
        return "▏"
    filled = int(value / max_value * width)
    if filled == 0 and value > 0:
        return "▏"
    return "█" * filled


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _tokens_dict(sessions: list[dict]) -> dict[str, int]:
    t = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "reasoning": 0}
    for s in sessions:
        tk = s.get("tokens", {})
        for k in t:
            t[k] += int(tk.get(k, 0) or 0)
    return t


def _total_tool_calls(sessions: list[dict]) -> int:
    return sum(sum(t.get("count", 0) for t in s.get("tool_calls", [])) for s in sessions)


def _total_skill_loads(sessions: list[dict]) -> int:
    return sum(len(s.get("skills_loaded", [])) for s in sessions)


def _compute_skills_list(sessions: list[dict], insights: dict) -> list[dict]:
    """Get skills list, prefer global_insights, fallback to per-session computation."""
    skills = insights.get("skills", [])
    if skills:
        return skills
    counts: dict[str, dict] = {}
    for s in sessions:
        for sl in s.get("skills_loaded", []):
            name = sl.get("skill_name", "?")
            if name not in counts:
                counts[name] = {"name": name, "load_count": 0, "token_estimate": 0}
            counts[name]["load_count"] += 1
            counts[name]["token_estimate"] += sl.get("token_estimate", 0) or 0
    return sorted(counts.values(), key=lambda x: x["load_count"], reverse=True)


def _compute_entity_rollup(operations: list[dict]) -> list[dict]:
    """Group log-payload operations by workflow-id."""
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
        last = steps_sorted[-1]
        status = last.get("status", "unknown")
        finalized = any((s.get("metadata") or {}).get("stage") == "finalize"
                        and s.get("status") == "success" for s in steps_sorted)
        if finalized:
            final_status = "success"
        elif status == "failure":
            final_status = "failure"
        elif status == "success":
            final_status = "abandoned"
        else:
            final_status = status
        entities.append({
            "entity_id": wf_id, "tool_name": steps_sorted[0].get("tool_name", "?"),
            "command": steps_sorted[0].get("command", "?"), "status": final_status,
            "total_duration_ms": sum(s.get("duration_ms", 0) or 0 for s in steps_sorted),
            "start_time": steps_sorted[0].get("started_at"),
            "end_time": steps_sorted[-1].get("finished_at"),
            "steps": steps_sorted, "is_workflow": True,
        })
    for op in standalones:
        entities.append({
            "entity_id": f"std_{op.get('source_file', '')}",
            "tool_name": op.get("tool_name", "?"), "command": op.get("command", "?"),
            "status": op.get("status", "unknown"),
            "total_duration_ms": op.get("duration_ms", 0) or 0,
            "start_time": op.get("started_at"), "end_time": op.get("finished_at"),
            "steps": [op], "is_workflow": False,
        })
    return entities


# ══════════════════════════════════════════════════════════════════════
# Header banner
# ══════════════════════════════════════════════════════════════════════

def _header(snap: dict, title: str = "HERMES ANALYTICS") -> None:
    print()
    print(_banner(f"📊  {title}"))
    print(_top(f"Snapshot: {_fmt_ts(snap.get('generated_at', ''))}"))
    print(_bot())
    print()


# ──────────────────────────────────────────────────────────────────────
# Separator
# ──────────────────────────────────────────────────────────────────────

def _gap() -> None:
    print()


# ══════════════════════════════════════════════════════════════════════
# GENERAL OVERVIEW — one compact panel per dashboard
# ══════════════════════════════════════════════════════════════════════

def _overview_sessions(sessions: list[dict]) -> int:
    """Returns number of sessions shown (0 = none)."""
    if not sessions:
        return 0
    total = len(sessions)
    msgs = sum(s.get("stats", {}).get("message_count", 0) for s in sessions)
    tools = _total_tool_calls(sessions)
    models = sorted(set(s.get("model") or "?" for s in sessions))
    model_str = ", ".join(models[:4])
    if len(models) > 4:
        model_str += f" +{len(models) - 4}"

    print(_top("📋 SESSIONS"))
    print(_row(f"  {total} sessions · {_num(msgs)} messages · {_num(tools)} tool calls"))
    print(_row(f"  Models: {model_str}"))
    print(_row(""))
    print(_row(f"  {_hint('sessions')}"))
    print(_bot())
    _gap()
    return total


def _overview_tokens(sessions: list[dict]) -> int:
    t = _tokens_dict(sessions)
    total = sum(t.values())
    if total == 0:
        return 0
    parts = [f"In {_num(t['input'])}", f"Out {_num(t['output'])}"]
    if t["cache_read"]:
        parts.insert(1, f"Cache {_num(t['cache_read'])}")
    parts.append(f"Total {_num(total)}")

    print(_top("🔢 TOKENS"))
    print(_row(f"  {' · '.join(parts)}"))
    print(_row(""))
    print(_row(f"  {_hint('tokens')}"))
    print(_bot())
    _gap()
    return total


def _overview_skills(sessions: list[dict], insights: dict) -> int:
    skills = _compute_skills_list(sessions, insights)
    if not skills:
        return 0
    total_loads = _total_skill_loads(sessions)
    top = skills[:3]
    top_str = ", ".join(
        f"{_trunc(s.get('name') or s.get('skill_name', '?'), 18)}({s['load_count']})"
        for s in top
    )

    print(_top("⭐ SKILLS"))
    print(_row(f"  {total_loads} loads across {len(skills)} skills"))
    print(_row(f"  Top: {top_str}"))
    print(_row(""))
    print(_row(f"  {_hint('skills')}"))
    print(_bot())
    _gap()
    return len(skills)


def _overview_tools(insights: dict) -> int:
    tools = insights.get("tools", [])
    if not tools:
        return 0
    total_calls = sum(t["count"] for t in tools)
    top = tools[:3]
    top_str = ", ".join(
        f"{_trunc(t['name'], 18)}({t['count']})" for t in top
    )

    print(_top("🔧 TOOLS"))
    print(_row(f"  {total_calls} calls across {len(tools)} tools"))
    print(_row(f"  Top: {top_str}"))
    print(_row(""))
    print(_row(f"  {_hint('tools')}"))
    print(_bot())
    _gap()
    return len(tools)


def _overview_commands(insights: dict) -> int:
    cmds = insights.get("commands", {})
    total = cmds.get("total_commands", 0)
    failed = cmds.get("failed_commands", 0)
    if total == 0:
        return 0
    top = cmds.get("most_executed_commands", [])[:1]
    top_str = _trunc(top[0]["command"], 40) if top else "—"

    print(_top("💻 SHELL COMMANDS"))
    print(_row(f"  {total} total · {failed} failed"))
    if top:
        print(_row(f"  Top: {top_str} ({top[0]['count']}x)"))
    print(_row(""))
    print(_row(f"  {_hint('commands')}"))
    print(_bot())
    _gap()
    return total


def _overview_mindlayer(log_payloads: dict) -> int:
    ops = log_payloads.get("operations", [])
    if not ops or not log_payloads.get("available"):
        return 0
    entities = _compute_entity_rollup(ops)
    total = len(entities)
    success = sum(1 for e in entities if e["status"] == "success")

    print(_top("🧠 MINDLAYER SKILLS"))
    print(_row(f"  {total} executions · {_pct(success, total)} success rate"))
    print(_row(""))
    print(_row(f"  {_hint('mindlayer')}"))
    print(_bot())
    _gap()
    return total


# ══════════════════════════════════════════════════════════════════════
# DETAIL VIEWS — each shows top-5, ends with hint to go back to general
# ══════════════════════════════════════════════════════════════════════

def _detail_footer() -> None:
    """Print the 'go back' hint at bottom of every detail view."""
    print(_row(""))
    print(_row("  Run without flags for general overview"))
    print(_bot())
    print()


# ── Sessions ─────────────────────────────────────────────────────────

def _detail_sessions(sessions: list[dict]) -> None:
    if not sessions:
        print("No sessions found.")
        return
    total = len(sessions)
    msgs = sum(s.get("stats", {}).get("message_count", 0) for s in sessions)
    tools = _total_tool_calls(sessions)
    platforms = sorted(set(s.get("platform") or "?" for s in sessions))

    model_counts: dict[str, int] = defaultdict(int)
    for s in sessions:
        model_counts[s.get("model") or "?"] += 1
    model_top = sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:TOP_N]

    print()
    print(_top("📋 SESSIONS — DETAIL"))
    print(_row(f"  Total: {total} · Messages: {_num(msgs)} · Tool calls: {_num(tools)}"))
    print(_row(f"  Platforms: {', '.join(platforms) if platforms else '—'}"))
    print(_hline())

    top_sessions = sorted(sessions,
                          key=lambda s: s.get("stats", {}).get("message_count", 0),
                          reverse=True)[:TOP_N]
    print(_row("  Top by messages:"))
    for i, s in enumerate(top_sessions, 1):
        title = _trunc(s.get("chat_name") or f"#{s.get('session_id', '?')}", 24)
        m = s.get("stats", {}).get("message_count", 0)
        tc = sum(c.get("count", 0) for c in s.get("tool_calls", []))
        tok = sum(int(v or 0) for v in s.get("tokens", {}).values())
        dur = _session_duration(s)
        model = _trunc(s.get("model") or "?", 16)
        line = f"  {i}. {title}  {model}  {m}msg {tc}t {_num(tok)}tok {dur}"
        print(_row(line))

    print(_hline())
    model_str = " · ".join(f"{m}({c})" for m, c in model_top)
    print(_row(f"  Models: {model_str}"))
    if len(model_counts) > TOP_N:
        print(_row(f"         +{len(model_counts) - TOP_N} more"))
    _detail_footer()


def _session_duration(s: dict) -> str:
    started = s.get("started_at")
    ended = s.get("ended_at")
    if not started or not ended:
        return ""
    try:
        if isinstance(started, (int, float)):
            sd = datetime.fromtimestamp(started, tz=timezone.utc)
        else:
            sd = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        if isinstance(ended, (int, float)):
            ed = datetime.fromtimestamp(ended, tz=timezone.utc)
        else:
            ed = datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
        delta = (ed - sd).total_seconds()
        if delta <= 0:
            return ""
        return _fmt_duration(int(delta * 1000))
    except Exception:
        return ""


# ── Tokens ────────────────────────────────────────────────────────────

def _detail_tokens(sessions: list[dict]) -> None:
    t = _tokens_dict(sessions)
    total = sum(t.values())
    if total == 0:
        print("No token data.")
        return

    model_tokens: dict[str, dict] = defaultdict(
        lambda: {"input": 0, "output": 0, "sessions": 0})
    for s in sessions:
        m = s.get("model") or "?"
        tk = s.get("tokens", {})
        model_tokens[m]["input"] += int(tk.get("input", 0) or 0)
        model_tokens[m]["output"] += int(tk.get("output", 0) or 0)
        model_tokens[m]["sessions"] += 1

    ranked = sorted(model_tokens.items(),
                    key=lambda x: x[1]["input"] + x[1]["output"], reverse=True)[:TOP_N]

    print()
    print(_top("🔢 TOKENS — DETAIL"))
    print(_row(f"  Input: {_num(t['input'])} · Output: {_num(t['output'])}"))
    print(_row(f"  Cache read: {_num(t['cache_read'])} · Cache write: {_num(t['cache_write'])} · "
               f"Reasoning: {_num(t['reasoning'])}"))
    print(_row(f"  Combined: {_num(total)}"))
    print(_hline())

    print(_row("  By model:"))
    for i, (model, mt) in enumerate(ranked, 1):
        mtot = mt["input"] + mt["output"]
        line = (f"  {i}. {_trunc(model, 26)}  "
                f"in={_num(mt['input'])} out={_num(mt['output'])} "
                f"tot={_num(mtot)} ({mt['sessions']}sess)")
        print(_row(line))

    if len(model_tokens) > TOP_N:
        print(_row(f"  +{len(model_tokens) - TOP_N} more models"))
    _detail_footer()


# ── Skills ────────────────────────────────────────────────────────────

def _detail_skills(sessions: list[dict], insights: dict) -> None:
    skills = _compute_skills_list(sessions, insights)
    if not skills:
        print("No skill data.")
        return
    top = skills[:TOP_N]
    max_loads = max(s["load_count"] for s in top) if top else 1

    print()
    print(_top("⭐ SKILLS — DETAIL"))
    print(_row(f"  {len(skills)} skills · {sum(s['load_count'] for s in skills)} total loads"))
    print(_hline())
    for i, sk in enumerate(top, 1):
        name = _trunc(sk.get("name") or sk.get("skill_name", "?"), 32)
        loads = sk.get("load_count", 0)
        tokens_val = sk.get("token_estimate", 0)
        b = _bar(loads, max_loads, 12)
        line = f"  {i}. {name}  {loads}ld {_num(tokens_val)}tok {b}"
        print(_row(line))
    if len(skills) > TOP_N:
        print(_row(f"  +{len(skills) - TOP_N} more skills"))
    _detail_footer()


# ── Tools ─────────────────────────────────────────────────────────────

def _detail_tools(insights: dict) -> None:
    tools = insights.get("tools", [])
    if not tools:
        print("No tool data.")
        return
    top = tools[:TOP_N]
    max_calls = max(t["count"] for t in top) if top else 1
    total_calls = sum(t["count"] for t in tools)

    print()
    print(_top("🔧 TOOLS — DETAIL"))
    print(_row(f"  {len(tools)} tools · {total_calls} total calls"))
    print(_hline())
    for i, t in enumerate(top, 1):
        name = _trunc(t["name"], 38)
        count = t["count"]
        b = _bar(count, max_calls, 14)
        line = f"  {i}. {name}  {count}calls {b}"
        print(_row(line))
    if len(tools) > TOP_N:
        print(_row(f"  +{len(tools) - TOP_N} more tools"))
    _detail_footer()


# ── Shell Commands ────────────────────────────────────────────────────

def _detail_commands(insights: dict) -> None:
    cmds = insights.get("commands", {})
    total = cmds.get("total_commands", 0)
    failed = cmds.get("failed_commands", 0)
    most = cmds.get("most_executed_commands", [])[:TOP_N]
    failed_list = cmds.get("failed_commands_list", [])[:TOP_N]

    if total == 0:
        print("No command data.")
        return

    print()
    print(_top("💻 SHELL COMMANDS — DETAIL"))
    print(_row(f"  Total: {total} · Failed: {failed} ({_pct(failed, total)})"))
    print(_hline())

    if most:
        max_c = max(m["count"] for m in most) if most else 1
        print(_row("  Most executed:"))
        for i, cmd in enumerate(most, 1):
            name = _trunc(cmd["command"], 42)
            b = _bar(cmd["count"], max_c, 12)
            line = f"  {i}. {name} {cmd['count']}x {b}"
            print(_row(line))

    if failed_list:
        print(_hline())
        max_f = max(f["failure_count"] for f in failed_list) if failed_list else 1
        print(_row("  Most failed:"))
        for i, fcmd in enumerate(failed_list, 1):
            name = _trunc(fcmd["command"], 42)
            b = _bar(fcmd["failure_count"], max_f, 12)
            line = f"  {i}. {name} {fcmd['failure_count']}x {b}"
            print(_row(line))

    all_cmds = cmds.get("most_executed_commands", [])
    if len(all_cmds) > TOP_N:
        print(_row(f"  +{len(all_cmds) - TOP_N} more commands"))
    _detail_footer()


# ── Mindlayer Skills ──────────────────────────────────────────────────

def _detail_mindlayer(log_payloads: dict) -> None:
    ops = log_payloads.get("operations", [])
    if not ops or not log_payloads.get("available"):
        print("No Mindlayer Skills data.")
        return

    entities = _compute_entity_rollup(ops)
    total = len(entities)
    success = sum(1 for e in entities if e["status"] == "success")
    failed = sum(1 for e in entities if e["status"] in ("failure", "failed"))
    abandoned = sum(1 for e in entities if e["status"] == "abandoned")

    tool_time: dict[str, float] = defaultdict(float)
    tool_cnt: dict[str, int] = defaultdict(int)
    for e in entities:
        tool_time[e["tool_name"]] += e["total_duration_ms"]
        tool_cnt[e["tool_name"]] += 1
    top_tools = sorted(tool_time.items(), key=lambda x: x[1], reverse=True)[:TOP_N]

    cmd_time: dict[str, float] = defaultdict(float)
    cmd_cnt: dict[str, int] = defaultdict(int)
    for e in entities:
        cmd_time[e["command"]] += e["total_duration_ms"]
        cmd_cnt[e["command"]] += 1
    top_cmds = sorted(cmd_time.items(), key=lambda x: x[1], reverse=True)[:TOP_N]

    daily: dict[str, int] = defaultdict(int)
    for op in ops:
        ts = op.get("started_at", "")
        try:
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            daily[dt.strftime("%Y-%m-%d")] += 1
        except Exception:
            pass

    print()
    print(_top("🧠 MINDLAYER SKILLS — DETAIL"))
    print(_row(f"  Executions: {total} · {_pct(success, total)} success · "
               f"{failed} failed · {abandoned} abandoned"))
    print(_hline())

    if top_tools:
        total_ms = sum(v for _, v in top_tools)
        print(_row("  Tools by time:"))
        for i, (tn, dur) in enumerate(top_tools, 1):
            b = _bar(dur, total_ms, 12)
            line = f"  {i}. {_trunc(tn, 30)} {_fmt_duration(int(dur))} ({tool_cnt[tn]}x) {b}"
            print(_row(line))

    if top_cmds:
        print(_hline())
        total_cmd_ms = sum(v for _, v in top_cmds)
        print(_row("  Commands by time:"))
        for i, (cn, dur) in enumerate(top_cmds, 1):
            b = _bar(dur, total_cmd_ms, 12)
            line = f"  {i}. {_trunc(cn, 34)} {_fmt_duration(int(dur))} ({cmd_cnt[cn]}x) {b}"
            print(_row(line))

    if daily:
        sorted_days = sorted(daily.keys())[-7:]
        max_count = max(daily.values())
        print(_hline())
        print(_row("  Activity (last 7 days):"))
        for day in sorted_days:
            b = _bar(daily[day], max_count, 14)
            line = f"  {day[-5:]}  {b} {daily[day]}"
            print(_row(line))

    recent = sorted(ops, key=lambda x: x.get("started_at") or "", reverse=True)[:TOP_N]
    if recent:
        print(_hline())
        print(_row("  Recent:"))
        markers = {"success": "✓", "failure": "✗", "failed": "✗", "abandoned": "◌", "incomplete": "◌"}
        for op in recent:
            mk = markers.get(op.get("status", ""), "?")
            tool = _trunc(op.get("tool_name", "?"), 20)
            cmd = _trunc(op.get("command", "?"), 18)
            dur = _fmt_duration(op.get("duration_ms"))
            ts = _fmt_ts(op.get("started_at"), short=True)
            line = f"  {mk} {tool} {cmd} {dur} {ts}"
            print(_row(line))

    _detail_footer()


# ══════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════

def _footer(browser_tip: bool = True) -> None:
    print("─" * WIDTH)
    if browser_tip:
        print("  --mode browser → interactive dashboard  |  --mode both → CLI + browser")
    print()


# ══════════════════════════════════════════════════════════════════════
# Main renderer
# ══════════════════════════════════════════════════════════════════════

def render_cli(snapshot_path: str | None = None,
               dashboard: str | None = None) -> str | None:
    """Render CLI output. Returns None on success, error string on failure.

    dashboard: None → general overview
               'sessions'|'skills'|'tools'|'tokens'|'commands'|'mindlayer'
    """
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

    if not sessions and not (log_payloads.get("available") and
                             log_payloads.get("operations")):
        return "⚠️  Snapshot loaded but contains no data."

    if dashboard:
        _header(snap, title=f"{dashboard.upper()} DETAIL")
        mapping = {
            "sessions":  lambda: _detail_sessions(sessions),
            "tokens":    lambda: _detail_tokens(sessions),
            "skills":    lambda: _detail_skills(sessions, insights),
            "tools":     lambda: _detail_tools(insights),
            "commands":  lambda: _detail_commands(insights),
            "mindlayer": lambda: _detail_mindlayer(log_payloads),
        }
        fn = mapping.get(dashboard)
        if fn:
            fn()
        else:
            return f"❌ Unknown dashboard: {dashboard}\nValid: {', '.join(mapping)}"
        _footer(browser_tip=False)
    else:
        _header(snap)
        _overview_sessions(sessions)
        _overview_tokens(sessions)
        _overview_skills(sessions, insights)
        _overview_tools(insights)
        _overview_commands(insights)
        _overview_mindlayer(log_payloads)

        print(_top("💡 TIPS"))
        print(_row("  Drill down with a dashboard flag:"))
        print(_row("  --sessions  --skills  --tools  --tokens  --commands  --mindlayer"))
        print(_row("  --mode browser → interactive Streamlit dashboard"))
        print(_bot())
        _footer(browser_tip=False)

    return None


# ══════════════════════════════════════════════════════════════════════
# CLI entry (when run directly)
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Hermes Analytics CLI")
    p.add_argument("snapshot_path", nargs="?", default=None,
                   help="Path to snapshot_latest.json")
    p.add_argument("--sessions", action="store_true", help="Session detail")
    p.add_argument("--skills", action="store_true", help="Skills detail")
    p.add_argument("--tools", action="store_true", help="Tools detail")
    p.add_argument("--tokens", action="store_true", help="Token detail")
    p.add_argument("--commands", action="store_true", help="Shell commands detail")
    p.add_argument("--mindlayer", action="store_true", help="Mindlayer Skills detail")
    args = p.parse_args()

    dash_flags = ["sessions", "skills", "tools", "tokens", "commands", "mindlayer"]
    selected = [f for f in dash_flags if getattr(args, f)]
    if len(selected) > 1:
        print(f"⚠️  Only one dashboard flag at a time. Got: "
              f"{', '.join(selected)}", file=sys.stderr)
        sys.exit(1)

    err = render_cli(args.snapshot_path,
                     dashboard=selected[0] if selected else None)
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)
