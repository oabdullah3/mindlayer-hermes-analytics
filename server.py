#!/usr/bin/env python3
"""Hermes Analytics — Local Single-User REST API server.

Reads snapshot_latest.json directly (no multi-user storage).
Started by the /hermes-snapshot-analytics slash command.
Serves a single snapshot via core endpoints.
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

# Local server reads snapshot_latest.json from the repo root
_SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot_latest.json")


# ---------------------------------------------------------------------------
# Snapshot loading
# ---------------------------------------------------------------------------

def _load_snapshot() -> dict | None:
    """Load the local snapshot file. Returns None if not found or invalid."""
    if not os.path.isfile(_SNAPSHOT_PATH):
        return None
    try:
        with open(_SNAPSHOT_PATH) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[WARN] Failed to read {_SNAPSHOT_PATH}: {exc}", file=sys.stderr)
        return None


def _get_sessions(snapshot: dict) -> list[dict]:
    """Return sessions from snapshot."""
    return snapshot.get("sessions", [])


def _get_global_insights(snapshot: dict) -> dict:
    """Return global_insights from snapshot."""
    return snapshot.get("global_insights", {})


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _json(data, status=200):
    """Return a Flask JSON response."""
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
    snapshot = _load_snapshot()
    total_sessions = len(snapshot.get("sessions", [])) if snapshot else 0
    return _json({
        "status": "ok",
        "total_sessions": total_sessions,
        "has_data": snapshot is not None,
    })


# ---------------------------------------------------------------------------
# Snapshot serving
# ---------------------------------------------------------------------------

@app.route("/api/snapshots/latest")
def snapshots_latest():
    snapshot = _load_snapshot()
    if not snapshot:
        return _json(
            {"status": "error", "message": "No snapshot available."},
            503,
        )
    return _json(snapshot)


# ---------------------------------------------------------------------------
# Snapshot ingestion (for push-priority collector)
# ---------------------------------------------------------------------------

@app.route("/api/snapshots", methods=["POST"])
def snapshots_ingest():
    """Accept a snapshot POST from the collector."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return _error("Invalid JSON body", 400)

    if "sessions" not in data:
        return _error("Snapshot must include sessions", 400)

    # Write to snapshot_latest.json
    try:
        with open(_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        return _error(f"Failed to write snapshot: {e}", 500)

    session_count = len(data.get("sessions", []))
    return _json({
        "status": "ok",
        "sessions": session_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, 201)


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

@app.route("/api/skills")
def skills_list():
    snapshot = _load_snapshot()
    if not snapshot:
        return _json({"status": "error", "message": "No snapshot available."}, 503)
    skills = _get_global_insights(snapshot).get("skills", [])
    return _json(skills)


@app.route("/api/skills/<name>")
def skill_detail(name):
    snapshot = _load_snapshot()
    if not snapshot:
        return _json({"status": "error", "message": "No snapshot available."}, 503)
    matches = []
    for session in _get_sessions(snapshot):
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
    return _json({"skill_name": name, "load_count": len(matches), "sessions": matches})


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@app.route("/api/tools")
def tools_list():
    snapshot = _load_snapshot()
    if not snapshot:
        return _json({"status": "error", "message": "No snapshot available."}, 503)
    tools = _get_global_insights(snapshot).get("tools", [])
    return _json(tools)


@app.route("/api/tools/<name>")
def tool_detail(name):
    snapshot = _load_snapshot()
    if not snapshot:
        return _json({"status": "error", "message": "No snapshot available."}, 503)
    matches = []
    total_calls = 0
    for session in _get_sessions(snapshot):
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
    return _json({"tool_name": name, "total_calls": total_calls, "sessions": matches})


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@app.route("/api/sessions")
def sessions_list():
    snapshot = _load_snapshot()
    if not snapshot:
        return _json({"status": "error", "message": "No snapshot available."}, 503)
    return _json(_get_sessions(snapshot))


@app.route("/api/sessions/<session_id>")
def session_detail(session_id):
    snapshot = _load_snapshot()
    if not snapshot:
        return _json({"status": "error", "message": "No snapshot available."}, 503)

    # Try integer match first (Hermes session IDs are integers)
    try:
        sid_int = int(session_id)
    except ValueError:
        sid_int = session_id

    for session in _get_sessions(snapshot):
        if session.get("session_id") == sid_int or str(session.get("session_id")) == session_id:
            return _json(session)
    return _error("Session not found", 404)


# ---------------------------------------------------------------------------
# Refresh trigger
# ---------------------------------------------------------------------------

@app.route("/api/refresh", methods=["POST"])
def refresh():
    """Trigger a collector re-run."""
    collector_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collector.py")
    try:
        result = subprocess.run(
            [sys.executable, collector_path],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "HERMES_ANALYTICS_SERVER_PORT": str(PORT)},
        )
        return _json({
            "status": "ok" if result.returncode == 0 else "error",
            "output": (result.stdout or result.stderr)[:1000],
        })
    except subprocess.TimeoutExpired:
        return _error("Collection timed out", 504)
    except Exception as e:
        return _error(f"Collection failed: {e}", 500)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[hermes-analytics] Local server starting on port {PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
