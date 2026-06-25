#!/usr/bin/env python3
"""Hermes Analytics REST API server.

Multi-user analytics server with flat-file persistence per ADR-0002.
Serves snapshot data via JSON endpoints, accepts snapshot POSTs from
remote collectors with per-user storage, and supports single-user
local mode as fallback.

Reads from server_data/{username}/snapshot_*.json when available.
Falls back to snapshot_latest.json for local single-user mode.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

PORT = int(os.environ.get("PORT", 5555))
SERVER_DATA = os.path.join(os.getcwd(), "server_data")

# ---------------------------------------------------------------------------
# Snapshot persistence — flat-file, read-on-demand
# ---------------------------------------------------------------------------


def _find_latest_snapshot(user_dir: str) -> str | None:
    """Return the path to the most recent snapshot in a user directory."""
    snapshots = sorted(
        Path(user_dir).glob("snapshot_*.json"),
        key=lambda p: p.name,  # timestamp sortable as string
        reverse=True,
    )
    return str(snapshots[0]) if snapshots else None


def _load_json_file(path: str) -> dict | None:
    """Load and parse a JSON snapshot file. Returns None on failure."""
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Failed to read {path}: {exc}", file=sys.stderr)
        return None


def _load_all_users() -> dict[str, dict]:
    """
    Scan server_data/ and return {username: latest_snapshot_dict}.
    Returns empty dict if no server_data or no user directories.
    """
    users = {}
    if not os.path.isdir(SERVER_DATA):
        return users

    for entry in sorted(os.listdir(SERVER_DATA)):
        user_dir = os.path.join(SERVER_DATA, entry)
        if not os.path.isdir(user_dir):
            continue
        latest = _find_latest_snapshot(user_dir)
        if latest:
            snap = _load_json_file(latest)
            if snap:
                users[entry] = snap
    return users


def _load_all_user_snapshots(username: str) -> list[dict]:
    """Return all snapshots (full dicts) for a user, newest first."""
    user_dir = os.path.join(SERVER_DATA, username)
    if not os.path.isdir(user_dir):
        return []
    snapshots = []
    for path in sorted(
        Path(user_dir).glob("snapshot_*.json"),
        key=lambda p: p.name,
        reverse=True,
    ):
        snap = _load_json_file(str(path))
        if snap:
            snapshots.append(snap)
    return snapshots


def _load_single_user_local() -> dict | None:
    """Fallback: load snapshot_latest.json for local single-user mode."""
    path = os.path.join(os.getcwd(), "snapshot_latest.json")
    if not os.path.isfile(path):
        return None
    return _load_json_file(path)


def get_snapshot_for_user(username: str) -> dict | None:
    """
    Get the latest snapshot for a specific user.
    Also checks the local fallback if the user has no server_data entries.
    """
    all_users = _load_all_users()
    if username in all_users:
        return all_users[username]
    # Check local fallback
    local = _load_single_user_local()
    if local:
        # In local mode, treat the single snapshot as belonging to any user
        return local
    return None


def get_all_latest_snapshots() -> dict[str, dict]:
    """
    Return {username: latest_snapshot} for all users.
    Falls back to local mode with anonymous user if server_data is empty.
    """
    all_users = _load_all_users()
    if all_users:
        return all_users
    # Local fallback
    local = _load_single_user_local()
    if local:
        return {"local": local}
    return {}


def _snapshot_filename() -> str:
    """Generate a timestamped snapshot filename."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"snapshot_{ts}.json"


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _aggregate_sessions(snapshots: dict[str, dict], username: str | None = None) -> list[dict]:
    """Collect sessions from snapshots, optionally filtered by username."""
    sessions = []
    for user, snap in snapshots.items():
        if username and user != username:
            continue
        for s in snap.get("sessions", []):
            s = dict(s)
            s["_username"] = user
            sessions.append(s)
    return sessions


def _aggregate_skills(snapshots: dict[str, dict], username: str | None = None) -> list[dict]:
    """Aggregate skill data across snapshots."""
    skill_map: dict[str, dict] = {}
    for user, snap in snapshots.items():
        if username and user != username:
            continue
        for skill in snap.get("global_insights", {}).get("skills", []):
            name = skill.get("skill_name", skill.get("name", "unknown"))
            if name not in skill_map:
                skill_map[name] = dict(skill)
                skill_map[name]["skill_name"] = name
                skill_map[name]["total_loads"] = skill.get("total_loads", skill.get("load_count", 0))
                skill_map[name]["users"] = []
            else:
                skill_map[name]["total_loads"] = (
                    skill_map[name].get("total_loads", 0)
                    + skill.get("total_loads", skill.get("load_count", 0))
                )
            if user not in skill_map[name]["users"]:
                skill_map[name]["users"].append(user)
    return sorted(skill_map.values(), key=lambda s: s.get("total_loads", 0), reverse=True)


def _aggregate_tools(snapshots: dict[str, dict], username: str | None = None) -> list[dict]:
    """Aggregate tool data across snapshots."""
    tool_map: dict[str, dict] = {}
    for user, snap in snapshots.items():
        if username and user != username:
            continue
        for tool in snap.get("global_insights", {}).get("tools", []):
            name = tool.get("tool_name", tool.get("name", "unknown"))
            if name not in tool_map:
                tool_map[name] = dict(tool)
                tool_map[name]["tool_name"] = name
                tool_map[name]["total_calls"] = tool.get("total_calls", tool.get("call_count", 0))
                tool_map[name]["users"] = []
            else:
                tool_map[name]["total_calls"] = (
                    tool_map[name].get("total_calls", 0)
                    + tool.get("total_calls", tool.get("call_count", 0))
                )
            if user not in tool_map[name]["users"]:
                tool_map[name]["users"].append(user)
    return sorted(tool_map.values(), key=lambda t: t.get("total_calls", 0), reverse=True)


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _json(data, status=200):
    """Return a Flask JSON response with optional pretty-printing."""
    pretty = request.args.get("pretty-print", "").lower() in ("1", "true", "yes")
    indent = 2 if pretty else None
    response = app.response_class(
        response=json.dumps(data, indent=indent, default=str),
        status=status,
        mimetype="application/json",
    )
    return response


def _error(message, status):
    return _json({"error": message}, status)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    total_sessions = sum(len(s.get("sessions", [])) for s in snapshots.values())
    return _json({
        "status": "ok",
        "users": len(snapshots),
        "total_sessions": total_sessions,
    })


# ---------------------------------------------------------------------------
# Snapshot serving
# ---------------------------------------------------------------------------

@app.route("/api/snapshots/latest")
def snapshots_latest():
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    username = request.args.get("username")
    if username:
        snap = snapshots.get(username)
        if not snap:
            return _error(f"No snapshots found for user: {username}", 404)
        return _json(snap)
    # Aggregate all
    return _json({
        "users": list(snapshots.keys()),
        "snapshots": snapshots,
    })


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

@app.route("/api/skills")
def skills_list():
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    username = request.args.get("username")
    skills = _aggregate_skills(snapshots, username=username)
    return _json(skills)


@app.route("/api/skills/<name>")
def skill_detail(name):
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    username = request.args.get("username")
    matches = []
    for user, snap in snapshots.items():
        if username and user != username:
            continue
        for session in snap.get("sessions", []):
            for sl in session.get("skills_loaded", []):
                if sl.get("skill_name") == name:
                    matches.append({
                        "session_id": session.get("session_id"),
                        "started_at": session.get("started_at"),
                        "model": session.get("model"),
                        "platform": session.get("platform"),
                        "user": user,
                        "load_timestamp": sl.get("load_timestamp"),
                        "preceding_user_message": sl.get("preceding_user_message"),
                        "token_estimate": sl.get("token_estimate"),
                        "content_chars": sl.get("content_chars"),
                    })
    if not matches:
        return _error("Skill not found", 404)
    return _json({
        "skill_name": name,
        "load_count": len(matches),
        "sessions": matches,
    })


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@app.route("/api/tools")
def tools_list():
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    username = request.args.get("username")
    tools = _aggregate_tools(snapshots, username=username)
    return _json(tools)


@app.route("/api/tools/<name>")
def tool_detail(name):
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    username = request.args.get("username")
    matches = []
    total_calls = 0
    for user, snap in snapshots.items():
        if username and user != username:
            continue
        for session in snap.get("sessions", []):
            for tc in session.get("tool_calls", []):
                if tc.get("tool_name") == name:
                    matches.append({
                        "session_id": session.get("session_id"),
                        "started_at": session.get("started_at"),
                        "model": session.get("model"),
                        "user": user,
                        "call_count": tc.get("count", 0),
                        "message_ids": tc.get("message_ids", []),
                    })
                    total_calls += tc.get("count", 0)
    if not matches:
        return _error("Tool not found", 404)
    return _json({
        "tool_name": name,
        "total_calls": total_calls,
        "sessions": matches,
    })


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@app.route("/api/sessions")
def sessions_list():
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    username = request.args.get("username")
    sessions = _aggregate_sessions(snapshots, username=username)
    return _json(sessions)


@app.route("/api/sessions/<session_id>")
def session_detail(session_id):
    snapshots = get_all_latest_snapshots()
    if not snapshots:
        return _json(
            {"status": "error", "message": "No snapshot available. Run userend/collector.py first."},
            503,
        )
    username = request.args.get("username")
    for user, snap in snapshots.items():
        if username and user != username:
            continue
        for session in snap.get("sessions", []):
            if session.get("session_id") == session_id:
                result = dict(session)
                result["_username"] = user
                return _json(result)
    return _error("Session not found", 404)


# ---------------------------------------------------------------------------
# Remote ingestion (ADR-0002 flat-file persistence)
# ---------------------------------------------------------------------------

@app.route("/api/snapshots", methods=["POST"])
def snapshots_create():
    if not request.is_json:
        return _error("Content-Type must be application/json", 400)

    body = request.get_json(silent=True)
    if body is None:
        return _error("Invalid JSON", 400)

    # Validate username (required per ADR-0002)
    username = body.get("username")
    if not username or not isinstance(username, str) or not username.strip():
        return _error("Missing required field: username", 422)

    # Validate required fields
    missing = []
    if "sessions" not in body:
        missing.append("sessions")
    if "global_insights" not in body:
        missing.append("global_insights")
    if missing:
        return _error(f"Missing required fields: {', '.join(missing)}", 422)

    # Create server_data/{username}/ directory
    user_dir = os.path.join(SERVER_DATA, username.strip())
    os.makedirs(user_dir, exist_ok=True)

    # Write timestamped snapshot
    filename = _snapshot_filename()
    filepath = os.path.join(user_dir, filename)

    # Ensure generated_at is set
    if "generated_at" not in body:
        body["generated_at"] = datetime.now(timezone.utc).isoformat()
    # Ensure username is embedded
    body["username"] = username.strip()

    with open(filepath, "w") as fh:
        json.dump(body, fh, indent=2, default=str)

    session_count = len(body.get("sessions", []))
    print(f"[INFO] Accepted snapshot for user '{username}': {session_count} sessions → {filepath}")

    return _json({"status": "accepted", "sessions": session_count}, 201)


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------

@app.route("/api/users")
def users_list():
    snapshots = get_all_latest_snapshots()
    result = []
    for username in sorted(snapshots.keys()):
        # Count actual files on disk
        user_dir = os.path.join(SERVER_DATA, username)
        count = len(list(Path(user_dir).glob("snapshot_*.json"))) if os.path.isdir(user_dir) else 1
        result.append({
            "username": username,
            "snapshot_count": count,
        })
    return _json(result)


@app.route("/api/users/<username>/latest")
def user_latest(username):
    snap = get_snapshot_for_user(username)
    if snap is None:
        return _error(f"No snapshots found for user: {username}", 404)
    return _json(snap)


@app.route("/api/users/<username>/history")
def user_history(username):
    user_dir = os.path.join(SERVER_DATA, username)
    if not os.path.isdir(user_dir):
        return _error(f"No snapshots found for user: {username}", 404)

    snapshots = sorted(
        Path(user_dir).glob("snapshot_*.json"),
        key=lambda p: p.name,
        reverse=True,
    )
    if not snapshots:
        return _error(f"No snapshots found for user: {username}", 404)

    timestamps = []
    for p in snapshots:
        # Extract timestamp from filename: snapshot_YYYY-MM-DD_HHMMSS.json
        name = p.stem  # e.g., snapshot_2026-06-24_091523
        ts = name[len("snapshot_"):]  # e.g., 2026-06-24_091523
        timestamps.append(ts)

    return _json(timestamps)


@app.route("/api/users/<username>/<timestamp>")
def user_timestamp(username, timestamp):
    filename = f"snapshot_{timestamp}.json"
    filepath = os.path.join(SERVER_DATA, username, filename)

    if not os.path.isfile(filepath):
        # Check local fallback
        local = _load_single_user_local()
        if local and local.get("generated_at", "").replace(":", "-").startswith(timestamp):
            return _json(local)
        return _error(f"Snapshot not found: {username}/{timestamp}", 404)

    snap = _load_json_file(filepath)
    if snap is None:
        return _error(f"Failed to load snapshot: {username}/{timestamp}", 500)

    return _json(snap)


# ---------------------------------------------------------------------------
# Leaderboard endpoints
# ---------------------------------------------------------------------------

@app.route("/api/leaderboard/sessions")
def leaderboard_sessions():
    snapshots = get_all_latest_snapshots()
    rankings = []
    for user, snap in snapshots.items():
        rankings.append({
            "username": user,
            "total_sessions": len(snap.get("sessions", [])),
        })
    rankings.sort(key=lambda r: r["total_sessions"], reverse=True)
    return _json(rankings)


@app.route("/api/leaderboard/skills")
def leaderboard_skills():
    snapshots = get_all_latest_snapshots()
    rankings = []
    for user, snap in snapshots.items():
        total = sum(
            len(s.get("skills_loaded", []))
            for s in snap.get("sessions", [])
        )
        rankings.append({
            "username": user,
            "total_skill_loads": total,
        })
    rankings.sort(key=lambda r: r["total_skill_loads"], reverse=True)
    return _json(rankings)


@app.route("/api/leaderboard/tools")
def leaderboard_tools():
    snapshots = get_all_latest_snapshots()
    rankings = []
    for user, snap in snapshots.items():
        total = sum(
            len(s.get("tool_calls", []))
            for s in snap.get("sessions", [])
        )
        rankings.append({
            "username": user,
            "total_tool_calls": total,
        })
    rankings.sort(key=lambda r: r["total_tool_calls"], reverse=True)
    return _json(rankings)


# ---------------------------------------------------------------------------
# Refresh trigger
# ---------------------------------------------------------------------------

@app.route("/api/refresh", methods=["POST"])
def refresh():
    try:
        result = subprocess.run(
            ["python3", "userend/collector.py"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.getcwd(),
        )
    except subprocess.TimeoutExpired:
        return _error("Collector timed out after 60s", 504)

    if result.returncode != 0:
        return _json(
            {
                "error": "Collector failed",
                "details": result.stderr.strip() or result.stdout.strip(),
            },
            500,
        )

    # Return the latest aggregated data
    snapshots = get_all_latest_snapshots()
    return _json({
        "status": "refreshed",
        "users": list(snapshots.keys()),
        "total_sessions": sum(len(s.get("sessions", [])) for s in snapshots.values()),
    })


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 56)
    print("  Hermes Analytics REST API (multi-user)")
    print("=" * 56)

    snapshots = get_all_latest_snapshots()
    if snapshots:
        total = sum(len(s.get("sessions", [])) for s in snapshots.values())
        print(f"  Users    : {len(snapshots)} ({', '.join(snapshots.keys())})")
        print(f"  Sessions : {total} total")
    else:
        print("  No snapshots loaded (run userend/collector.py or POST /api/snapshots)")

    print(f"  Port     : {PORT}")
    print("-" * 56)
    print("  Endpoints:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.rule.startswith("/api/"):
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            print(f"    {methods:8s} {rule.rule}")
    print("=" * 56)

    app.run(host="0.0.0.0", port=PORT, debug=False)
