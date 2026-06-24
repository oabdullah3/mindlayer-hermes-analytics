#!/usr/bin/env python3
"""Hermes Analytics REST API server.

Serves snapshot data as JSON endpoints for Grafana dashboards and remote
consumers. Reads snapshot_latest.json on startup, serves structured
sub-resources, accepts snapshot POSTs from remote collectors, and exposes
a refresh endpoint to re-run collector.py.
"""

import json
import os
import subprocess
import sys

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

PORT = int(os.environ.get("PORT", 5555))

# ---------------------------------------------------------------------------
# Snapshot state (module-level, loaded at startup and on refresh)
# ---------------------------------------------------------------------------

_SNAPSHOT: dict | None = None


def load_snapshot() -> dict | None:
    """Read snapshot_latest.json into memory.

    Returns the parsed dict on success, or None if the file is missing
    or invalid.
    """
    path = os.path.join(os.getcwd(), "snapshot_latest.json")
    if not os.path.isfile(path):
        print(f"[WARN] snapshot_latest.json not found at {path}", file=sys.stderr)
        return None
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print("[WARN] snapshot_latest.json is not a JSON object", file=sys.stderr)
            return None
        print(f"[INFO] Loaded snapshot: {len(data.get('sessions', []))} sessions")
        return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Failed to read snapshot_latest.json: {exc}", file=sys.stderr)
        return None


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


def _require_snapshot():
    """Return the loaded snapshot or a 503 error response."""
    if _SNAPSHOT is None:
        return None, _json(
            {"status": "error", "message": "No snapshot available. Run collector.py first."},
            503,
        )
    return _SNAPSHOT, None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    if _SNAPSHOT is None:
        return _json(
            {"status": "error", "message": "No snapshot available. Run collector.py first."},
            503,
        )
    return _json({
        "status": "ok",
        "last_collection": _SNAPSHOT.get("generated_at"),
    })


# ---------------------------------------------------------------------------
# Snapshot serving
# ---------------------------------------------------------------------------

@app.route("/api/snapshots/latest")
def snapshots_latest():
    snap, err = _require_snapshot()
    if err:
        return err
    return _json(snap)


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

@app.route("/api/skills")
def skills_list():
    snap, err = _require_snapshot()
    if err:
        return err
    skills = snap.get("global_insights", {}).get("skills", [])
    return _json(skills)


@app.route("/api/skills/<name>")
def skill_detail(name):
    snap, err = _require_snapshot()
    if err:
        return err
    sessions = snap.get("sessions", [])
    matches = []
    for session in sessions:
        for sl in session.get("skills_loaded", []):
            if sl.get("skill_name") == name:
                matches.append({
                    "session_id": session.get("session_id"),
                    "started_at": session.get("started_at"),
                    "model": session.get("model"),
                    "platform": session.get("platform"),
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
    snap, err = _require_snapshot()
    if err:
        return err
    tools = snap.get("global_insights", {}).get("tools", [])
    return _json(tools)


@app.route("/api/tools/<name>")
def tool_detail(name):
    snap, err = _require_snapshot()
    if err:
        return err
    sessions = snap.get("sessions", [])
    matches = []
    total_calls = 0
    for session in sessions:
        for tc in session.get("tool_calls", []):
            if tc.get("tool_name") == name:
                matches.append({
                    "session_id": session.get("session_id"),
                    "started_at": session.get("started_at"),
                    "model": session.get("model"),
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
    snap, err = _require_snapshot()
    if err:
        return err
    sessions = snap.get("sessions", [])
    return _json(sessions)


@app.route("/api/sessions/<session_id>")
def session_detail(session_id):
    snap, err = _require_snapshot()
    if err:
        return err
    for session in snap.get("sessions", []):
        if session.get("session_id") == session_id:
            return _json(session)
    return _error("Session not found", 404)


# ---------------------------------------------------------------------------
# Remote ingestion
# ---------------------------------------------------------------------------

@app.route("/api/snapshots", methods=["POST"])
def snapshots_create():
    global _SNAPSHOT

    if not request.is_json:
        return _error("Content-Type must be application/json", 400)

    body = request.get_json(silent=True)
    if body is None:
        return _error("Invalid JSON", 400)

    # Validate required fields
    missing = []
    if "sessions" not in body:
        missing.append("sessions")
    if "global_insights" not in body:
        missing.append("global_insights")
    if missing:
        return _error(f"Missing required fields: {', '.join(missing)}", 422)

    _SNAPSHOT = body
    session_count = len(body.get("sessions", []))
    print(f"[INFO] Accepted remote snapshot: {session_count} sessions")
    return _json({"status": "accepted", "sessions": session_count}, 201)


# ---------------------------------------------------------------------------
# Refresh trigger
# ---------------------------------------------------------------------------

@app.route("/api/refresh", methods=["POST"])
def refresh():
    global _SNAPSHOT

    try:
        result = subprocess.run(
            ["python3", "collector.py"],
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

    # Reload the newly generated snapshot
    new_snap = load_snapshot()
    if new_snap is None:
        return _error("Collector ran but snapshot could not be loaded", 500)

    _SNAPSHOT = new_snap
    return _json(_SNAPSHOT)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 56)
    print("  Hermes Analytics REST API")
    print("=" * 56)

    _SNAPSHOT = load_snapshot()
    if _SNAPSHOT:
        print(f"  Snapshot : {len(_SNAPSHOT.get('sessions', []))} sessions loaded")
    else:
        print("  Snapshot : NOT LOADED (run collector.py first)")

    print(f"  Port     : {PORT}")
    print("-" * 56)
    print("  Endpoints:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.rule.startswith("/api/"):
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            print(f"    {methods:8s} {rule.rule}")
    print("=" * 56)

    app.run(host="0.0.0.0", port=PORT, debug=False)
