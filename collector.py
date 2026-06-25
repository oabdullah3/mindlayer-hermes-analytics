#!/usr/bin/env python3
"""
Hermes Analytics — Data Collector

Reads Hermes Agent data sources from ~/.hermes/ and produces a structured
snapshot JSON file consumed by the REST API server and Grafana dashboards.

Usage:
    python collector.py                  # local mode
    HERMES_ANALYTICS_REMOTE=https://...  python collector.py   # push mode

9-step extraction pipeline:
    1. Session list (state.db sessions table)
    2. Skill load detection (assistant tool_calls → skill_view → tool response)
    3. Preceding user messages (message before each skill load)
    4. Tool call aggregation (per-session tool_name → count + message_ids)
    5. Token estimation (CEIL(LENGTH(content) / 4) per skill load)
    6. Session user messages (all user messages, truncated to 200 chars)
    7. Error parsing (agent.log lines)
    8. Shell command extraction (terminal tool calls)
    9. Log payloads extraction (log_payloads/YYYY-MM-DD/*.json)
"""

import argparse
import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone


# ──────────────────────────────────────────────────────────────────────────────
# Foundation (Tasks 1.1 – 1.4)
# ──────────────────────────────────────────────────────────────────────────────

def resolve_hermes_home() -> str:
    """Resolve HERMES_HOME from env var, defaulting to ~/.hermes."""
    home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    return home


def validate_state_db(hermes_home: str) -> str:
    """Check that state.db exists, exit with error if missing."""
    db_path = os.path.join(hermes_home, "state.db")
    if not os.path.isfile(db_path):
        print(f"ERROR: state.db not found at {db_path}", file=sys.stderr)
        sys.exit(1)
    return db_path


def open_db_readonly(db_path: str) -> sqlite3.Connection:
    """Open state.db in read-only mode via URI."""
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Session Extraction (Tasks 2.1 – 2.3)
# ──────────────────────────────────────────────────────────────────────────────

def extract_sessions(conn: sqlite3.Connection) -> list[dict]:
    """Query all sessions from state.db, ordered by started_at DESC."""
    cursor = conn.execute("SELECT * FROM sessions ORDER BY started_at DESC")
    rows = cursor.fetchall()

    if not rows:
        return []

    sessions = []
    # Derive column names from cursor.description to be robust against schema drift
    columns = [desc[0] for desc in cursor.description]
    for row in rows:
        session = dict(zip(columns, row))
        sessions.append(session)

    return sessions


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: Skill Load Detection (Tasks 3.1 – 3.5)
# ──────────────────────────────────────────────────────────────────────────────

SKILL_TOOL_NAMES = ("skill_view", "skill_manage")


def detect_skill_loads(
    conn: sqlite3.Connection, session_id: int
) -> list[dict]:
    """
    For a given session, find all skill loads:
      - Query assistant messages with tool_calls referencing skill_view/skill_manage
      - Fetch the linked tool response
      - Parse the skill name from the response content JSON
    """
    skills = []

    # Find assistant messages that called skill_view or skill_manage
    cursor = conn.execute(
        """
        SELECT id, tool_calls, timestamp
        FROM messages
        WHERE session_id = ?
          AND role = 'assistant'
          AND tool_calls IS NOT NULL
        ORDER BY id ASC
        """,
        (session_id,),
    )

    for row in cursor:
        tool_calls_raw = row["tool_calls"]
        if not tool_calls_raw:
            continue

        try:
            tool_calls = json.loads(tool_calls_raw)
        except (json.JSONDecodeError, TypeError):
            print(
                f"WARNING: Malformed tool_calls JSON at message {row['id']} "
                f"in session {session_id}",
                file=sys.stderr,
            )
            continue

        # tool_calls can be a list; check each for skill_load
        for tc in tool_calls:
            func_name = tc.get("function", {}).get("name", "")
            if func_name not in SKILL_TOOL_NAMES:
                continue

            call_id = tc.get("id")
            if not call_id:
                print(
                    f"WARNING: skill_view call at message {row['id']} "
                    f"has no id field in tool_calls",
                    file=sys.stderr,
                )
                continue

            # Fetch the linked tool response
            tool_row = conn.execute(
                """
                SELECT id, content, timestamp, tool_call_id
                FROM messages
                WHERE session_id = ?
                  AND role = 'tool'
                  AND tool_call_id = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (session_id, call_id),
            ).fetchone()

            if tool_row is None:
                print(
                    f"WARNING: Orphaned skill call — assistant message "
                    f"{row['id']} references tool_call_id={call_id} "
                    f"with no matching tool response in session {session_id}",
                    file=sys.stderr,
                )
                continue

            # Parse skill name from tool response content JSON
            skill_name = _parse_skill_name(
                tool_row["content"], tool_row["id"], session_id
            )

            content = tool_row["content"] or ""
            content_chars = len(content)
            token_estimate = math.ceil(content_chars / 4) if content_chars > 0 else 0

            skills.append(
                {
                    "skill_name": skill_name,
                    "load_message_id": row["id"],
                    "load_timestamp": row["timestamp"],
                    "tool_call_id": call_id,
                    "content_chars": content_chars,
                    "token_estimate": token_estimate,
                }
            )

    return skills


def _parse_skill_name(content: str | None, msg_id: int, session_id: int) -> str:
    """Extract the skill name from a skill_view tool response content.

    Hermes writes skill_view responses in 3+ formats:
      1. JSON success: {"success": true, "name": "confluence-skill", ...}
      2. JSON failure: {"success": false, "error": "Skill 'jira-skill' not found.", ...}
      3. Bracketed text: [skill_view] name=confluence-skill (25,532 chars)
      4. Duplicate placeholder: [Duplicate tool output — ...]
    """
    if not content:
        print(
            f"WARNING: Empty content in skill_view tool response "
            f"at message {msg_id} in session {session_id}",
            file=sys.stderr,
        )
        return "unknown"

    # ── Format 1 & 2: JSON ──────────────────────────────────────────
    if content.startswith("{"):
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            # The content may be valid JSON with trailing text appended
            # (e.g., "[Tool loop warning: ...]" after a JSON object).
            # Use raw_decode to consume only the first JSON value.
            try:
                parsed, _ = json.JSONDecoder().raw_decode(content)
            except (json.JSONDecodeError, TypeError):
                print(
                    f"WARNING: Malformed content JSON in skill_view tool response "
                    f"at message {msg_id} in session {session_id}",
                    file=sys.stderr,
                )
                return "unknown"

        if isinstance(parsed, dict):
            # Common keys: name, skill_name, skill
            name = parsed.get("name") or parsed.get("skill_name") or parsed.get("skill")
            if name:
                return name

            # Fallback: extract from error message like "Skill 'X' not found."
            error = parsed.get("error", "")
            if error:
                # Pattern 1: "Skill 'jira-skill' not found."
                match = re.match(r"Skill\s+'([^']+)'", error)
                if match:
                    return match.group(1)
                # Pattern 2: Security scan "Scan: chrome-devtools-mcp-guide (...)"
                match = re.search(r"Scan:\s+(\S+)", error)
                if match:
                    return match.group(1)
                # Pattern 3: "Skill name is required." — truly unknown
                if "skill name is required" in error.lower():
                    return "unknown"
                print(
                    f"WARNING: JSON response with unrecognized error format at "
                    f"message {msg_id} in session {session_id}",
                    file=sys.stderr,
                )
            return "unknown"

    # ── Format 3: Bracketed text "[skill_view] name=SKILL (...)" ─────
    if content.startswith("[skill_view]"):
        match = re.match(r"\[skill_view\]\s+name=(\S+)", content)
        if match:
            return match.group(1)
        print(
            f"WARNING: Unrecognized bracketed format in skill_view "
            f"response at message {msg_id} in session {session_id}",
            file=sys.stderr,
        )
        return "unknown"

    # ── Format 4: Duplicate placeholder "[Duplicate ...]" ────────────
    if content.startswith("[Duplicate"):
        # This is not a real skill load — a prior response had the content
        print(
            f"INFO: Duplicate tool output at message {msg_id} "
            f"in session {session_id} — skipping",
            file=sys.stderr,
        )
        return "unknown"

    # ── Unknown format ───────────────────────────────────────────────
    print(
        f"WARNING: Unknown content format in skill_view tool response "
        f"at message {msg_id} in session {session_id}: "
        f"{content[:100]}",
        file=sys.stderr,
    )
    return "unknown"

    return "unknown"


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: Preceding User Messages (Tasks 4.1 – 4.3)
# ──────────────────────────────────────────────────────────────────────────────

def attach_preceding_user_messages(
    conn: sqlite3.Connection, skills: list[dict], session_id: int
) -> None:
    """
    For each skill load, find the message immediately before the load message
    (id - 1) in the same session. If it's a user message, attach its content.
    Mutates the skills list in place.
    """
    for skill in skills:
        load_msg_id = skill["load_message_id"]

        row = conn.execute(
            """
            SELECT id, role, content
            FROM messages
            WHERE session_id = ?
              AND id = ?
            """,
            (session_id, load_msg_id - 1),
        ).fetchone()

        if row is None:
            skill["preceding_user_message"] = None
        elif row["role"] == "user":
            skill["preceding_user_message"] = row["content"]
        else:
            skill["preceding_user_message"] = None


# ──────────────────────────────────────────────────────────────────────────────
# Step 4: Tool Call Aggregation (Tasks 5.1 – 5.3)
# ──────────────────────────────────────────────────────────────────────────────

def _parse_tool_calls_json(content: str | None) -> list[str]:
    """Parse tool_calls JSON and return list of function.name values.
    
    Returns empty list if content is null, empty, or malformed.
    """
    if not content:
        return []
    try:
        tool_calls = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(tool_calls, list):
        return []
    names = []
    for tc in tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name")
        if name:
            names.append(name)
    return names


def aggregate_tool_calls(
    conn: sqlite3.Connection, session_id: int
) -> list[dict]:
    """Aggregate tool calls per session by resolving names from tool_calls JSON.
    
    Per ADR visual-overhaul D1:
    - Query all assistant messages with non-null tool_calls
    - Parse function.name from each tool call entry
    - Match tool-response rows (role='tool') by position: the Nth tool response
      after an assistant message corresponds to the Nth entry in its tool_calls array
    - Compute success rate per tool name
    - Falls back to messages.tool_name column if all tool_calls are null/malformed
    """
    # ── Query assistant messages with tool_calls ──
    cursor = conn.execute(
        """
        SELECT id, tool_calls
        FROM messages
        WHERE session_id = ?
          AND role = 'assistant'
          AND tool_calls IS NOT NULL
        ORDER BY id ASC
        """,
        (session_id,),
    )
    assistant_rows = cursor.fetchall()

    # ── Build tool-name → {count, success_count, message_ids} map ──
    tool_map: dict[str, dict] = {}  # tool_name -> {count, success_count, msg_ids}

    for row in assistant_rows:
        names = _parse_tool_calls_json(row["tool_calls"])
        if not names:
            continue

        # Fetch the N tool-response rows (role='tool') that follow this assistant message.
        # Positional matching: 1st tool call → 1st tool response, etc.
        placeholders = ",".join("?" * len(names))
        tool_rows = conn.execute(
            f"""
            SELECT id, content
            FROM messages
            WHERE session_id = ?
              AND role = 'tool'
              AND id > ?
            ORDER BY id ASC
            LIMIT {len(names)}
            """,
            (session_id, row["id"]),
        ).fetchall()

        for i, name in enumerate(names):
            if name not in tool_map:
                tool_map[name] = {"count": 0, "success_count": 0, "msg_ids": []}
            tool_map[name]["count"] += 1

            # Check success from matching tool response (if available)
            if i < len(tool_rows):
                tr = tool_rows[i]
                tool_map[name]["msg_ids"].append(tr["id"])
                content = tr["content"] or ""
                # Success = non-empty content (tool completed)
                if content.strip():
                    tool_map[name]["success_count"] += 1

    # ── Fallback: use messages.tool_name if no results from tool_calls ──
    if not tool_map:
        fb_cursor = conn.execute(
            """
            SELECT tool_name, COUNT(*) AS cnt, GROUP_CONCAT(id) AS msg_ids
            FROM messages
            WHERE session_id = ? AND role = 'tool'
            GROUP BY tool_name
            ORDER BY cnt DESC
            """,
            (session_id,),
        )
        for fb_row in fb_cursor:
            name = fb_row["tool_name"] or "unknown"
            msg_ids_str = fb_row["msg_ids"] or ""
            msg_ids = [int(x) for x in msg_ids_str.split(",") if x]
            tool_map[name] = {
                "count": fb_row["cnt"],
                "success_count": fb_row["cnt"],  # assume success in fallback
                "msg_ids": msg_ids,
            }

    # ── Build result list ──
    tools = []
    for name, info in sorted(tool_map.items(), key=lambda x: x[1]["count"], reverse=True):
        total = info["count"]
        successes = info["success_count"]
        success_rate = round(successes / total, 3) if total > 0 else 0.0
        tools.append({
            "tool_name": name,
            "count": total,
            "success_rate": success_rate,
            "message_ids": info["msg_ids"],
        })

    return tools


# ──────────────────────────────────────────────────────────────────────────────
# Step 4a: Shell Command Extraction (capture-shell-commands)
# ──────────────────────────────────────────────────────────────────────────────

def extract_shell_commands(
    conn: sqlite3.Connection, session_id: int
) -> list[dict]:
    """
    For a given session, find all shell/terminal commands:
      - Query assistant messages with tool_calls JSON
      - Extract any tool call whose function.arguments contains a 'command' key
      - Match with the tool response to get exit code and output
      - Truncate output to 200 chars
    """
    commands: list[dict] = []

    cursor = conn.execute(
        """
        SELECT id, tool_calls, timestamp
        FROM messages
        WHERE session_id = ?
          AND role = 'assistant'
          AND tool_calls IS NOT NULL
        ORDER BY id ASC
        """,
        (session_id,),
    )

    for row in cursor:
        tool_calls_raw = row["tool_calls"]
        if not tool_calls_raw:
            continue

        try:
            tool_calls = json.loads(tool_calls_raw)
        except (json.JSONDecodeError, TypeError):
            print(
                f"WARNING: Malformed tool_calls JSON at message {row['id']} "
                f"in session {session_id}",
                file=sys.stderr,
            )
            continue

        for tc in tool_calls:
            fn = tc.get("function", {})
            args_raw = fn.get("arguments", "")
            if not args_raw:
                continue

            # Parse arguments — may be a JSON string
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except (json.JSONDecodeError, TypeError):
                continue

            command = args.get("command")
            if not command:
                continue

            call_id = tc.get("id")
            tool_name = fn.get("name", "unknown")
            timestamp = row["timestamp"]

            # Fetch the linked tool response
            exit_code = None
            output = None

            if call_id:
                tool_row = conn.execute(
                    """
                    SELECT id, content
                    FROM messages
                    WHERE session_id = ?
                      AND role = 'tool'
                      AND tool_call_id = ?
                    LIMIT 1
                    """,
                    (session_id, call_id),
                ).fetchone()

                if tool_row is not None:
                    exit_code, output = _parse_shell_response(
                        tool_row["content"], tool_row["id"], session_id
                    )
                else:
                    print(
                        f"WARNING: Orphaned shell command — assistant message "
                        f"{row['id']} references tool_call_id={call_id} "
                        f"with no matching tool response in session {session_id}",
                        file=sys.stderr,
                    )

            # Truncate output
            if output and len(output) > 200:
                output = output[:197] + "… (truncated)"

            # Determine success
            success = exit_code == 0 if exit_code is not None else None

            commands.append(
                {
                    "command": command,
                    "tool_name": tool_name,
                    "exit_code": exit_code,
                    "output": output,
                    "success": success,
                    "timestamp": timestamp,
                    "message_id": row["id"],
                    "tool_call_id": call_id,
                }
            )

    return commands


def _parse_shell_response(
    content: str | None, msg_id: int, session_id: int
) -> tuple[int | None, str | None]:
    """
    Parse a shell tool response to extract (exit_code, output).

    Formats handled:
      1. JSON: {"output": "...", "stdout": "..."}
      2. Bracketed text: [terminal] ran `CMD` -> exit N, ...
      3. Duplicate: [Duplicate tool output — ...]
      4. Cancelled: [Tool execution cancelled — ...]
      5. Error: Error executing tool: ...
      6. Missing tool: Tool 'X' does not exist. ...
    """
    if not content:
        print(
            f"WARNING: Empty content in shell tool response "
            f"at message {msg_id} in session {session_id}",
            file=sys.stderr,
        )
        return None, None

    # ── Format 1: JSON ──────────────────────────────────────────
    if content.startswith("{"):
        try:
            parsed, _ = json.JSONDecoder().raw_decode(content)
        except (json.JSONDecodeError, TypeError):
            parsed = None

        if isinstance(parsed, dict):
            out = parsed.get("output") or parsed.get("stdout") or ""
            # JSON format doesn't carry exit code — default 0
            return 0, out if out else None

        # Fall through to plain-text parsing

    # ── Format 2: Bracketed text [terminal] ran `CMD` -> exit N  ─
    if content.startswith("[terminal]") or content.startswith("["):
        # Use DOTALL — commands may embed newlines
        match = re.match(
            r"\[terminal\]\s+.*?->\s+exit\s+(\d+)", content, re.DOTALL
        )
        if match:
            exit_code = int(match.group(1))
            return exit_code, content

        # ── Format 3: Duplicate ─────────────────────────────────
        if content.startswith("[Duplicate"):
            print(
                f"INFO: Duplicate tool output at message {msg_id} "
                f"in session {session_id} — skipping",
                file=sys.stderr,
            )
            return -1, "[duplicate]"

        # ── Format 4: Cancelled ──────────────────────────────────
        if content.startswith("[Tool execution cancelled"):
            print(
                f"INFO: Tool execution cancelled at message {msg_id} "
                f"in session {session_id}",
                file=sys.stderr,
            )
            return -1, "[cancelled]"

        # Bracketed but unrecognized — return as output with null exit
        print(
            f"WARNING: Unrecognized bracketed format in shell "
            f"response at message {msg_id} in session {session_id}",
            file=sys.stderr,
        )
        return None, content

    # ── Format 5: Error executing tool ──────────────────────────
    if content.startswith("Error executing tool:"):
        return -1, content

    # ── Format 6: Missing tool ──────────────────────────────────
    if content.startswith("Tool '") and "does not exist" in content:
        return -1, content

    # ── Unknown format ──────────────────────────────────────────
    print(
        f"WARNING: Unknown content format in shell tool response "
        f"at message {msg_id} in session {session_id}: "
        f"{content[:100]}",
        file=sys.stderr,
    )
    return None, content


# ──────────────────────────────────────────────────────────────────────────────
# Step 5: Token Estimation (Tasks 6.1 – 6.2)
# ──────────────────────────────────────────────────────────────────────────────
# Token estimation is already computed during skill load detection
# (Step 2) as math.ceil(content_chars / 4). Step 5 is a no-op pass-through
# that validates the values are present.


def validate_token_estimates(skills: list[dict]) -> None:
    """Ensure every skill load has computed token_estimate and content_chars."""
    for skill in skills:
        if "token_estimate" not in skill:
            content_chars = skill.get("content_chars", 0)
            skill["token_estimate"] = (
                math.ceil(content_chars / 4) if content_chars > 0 else 0
            )
        if "content_chars" not in skill:
            skill["content_chars"] = 0


# ──────────────────────────────────────────────────────────────────────────────
# Step 6: Session User Messages (Tasks 7.1 – 7.3)
# ──────────────────────────────────────────────────────────────────────────────

def extract_user_messages(
    conn: sqlite3.Connection, session_id: int
) -> list[dict]:
    """Collect all user messages for a session, truncated to 200 chars."""
    cursor = conn.execute(
        """
        SELECT id, content, timestamp
        FROM messages
        WHERE session_id = ?
          AND role = 'user'
        ORDER BY id ASC
        """,
        (session_id,),
    )

    messages = []
    for row in cursor:
        content = row["content"] or ""
        truncated = content[:200] if len(content) > 200 else content
        messages.append(
            {
                "message_id": row["id"],
                "content": truncated,
                "timestamp": row["timestamp"],
            }
        )

    return messages


# ──────────────────────────────────────────────────────────────────────────────
# Step 7: Error Parsing (Tasks 8.1 – 8.3)
# ──────────────────────────────────────────────────────────────────────────────

# Regex for lines like:
#   [session_abc123] 2024-01-01 12:00:00,123 Tool terminal returned error (63.59s)
ERROR_RE = re.compile(
    r"\[([^\]]+)\]\s+([\d-]+\s+[\d:,]+)\s+Tool\s+terminal\s+returned\s+error\s+\(([\d.]+)s\)"
)


def parse_agent_log(hermes_home: str) -> dict[int, list[dict]]:
    """
    Parse agent.log for error lines.
    Returns a dict mapping session_id (numeric, if the bracketed prefix is numeric)
    to a list of error dicts.
    """
    log_path = os.path.join(hermes_home, "logs", "agent.log")
    if not os.path.isfile(log_path):
        print(
            f"INFO: agent.log not found at {log_path} — skipping error parsing",
            file=sys.stderr,
        )
        return {}

    errors_by_session: dict[int, list[dict]] = {}

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                match = ERROR_RE.search(line)
                if not match:
                    continue

                session_tag = match.group(1)
                timestamp = match.group(2)
                duration = float(match.group(3))

                # Try to extract a numeric session id from the tag
                # Common format: "session_<number>" or just "<number>"
                session_id = _parse_session_tag(session_tag)
                if session_id is None:
                    continue

                errors_by_session.setdefault(session_id, []).append(
                    {
                        "session_id": session_id,
                        "timestamp": timestamp,
                        "related_to": "Tool terminal returned error",
                        "duration_s": duration,
                    }
                )
    except OSError as e:
        print(
            f"WARNING: Could not read agent.log: {e}",
            file=sys.stderr,
        )

    return errors_by_session


def _parse_session_tag(tag: str) -> int | None:
    """Extract a numeric session id from a bracketed tag string."""
    # Try "session_<number>"
    m = re.match(r"session[_]?(\d+)", tag)
    if m:
        return int(m.group(1))
    # Try bare integer
    try:
        return int(tag)
    except ValueError:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Step 8: Log Payloads Extraction (add-log-payloads-analytics)
# ──────────────────────────────────────────────────────────────────────────────

def extract_log_payloads(hermes_home: str) -> dict:
    """
    Discover and parse all JSON payload files under {hermes_home}/log_payloads/
    organized by date subdirectories (YYYY-MM-DD/*.json).

    Returns:
        {"operations": [...], "available": bool}
      - Each operation extracts: tool_name, command, user_email, status,
        started_at, finished_at, duration_ms, input_flags, metadata, error,
        result_size (computed), source_file (computed).
      - `result` is NOT stored; result_size = 0 if null/{} else len(json.dumps(result))
      - Malformed JSON files are skipped with a WARNING.
      - If the directory does not exist, returns {"operations": [], "available": False}.
    """
    log_payloads_dir = os.path.join(hermes_home, "log_payloads")
    if not os.path.isdir(log_payloads_dir):
        return {"operations": [], "available": False}

    # Known fields to extract (all except 'result')
    KNOWN_FIELDS = [
        "tool_name", "command", "user_email", "status",
        "started_at", "finished_at", "duration_ms",
        "input_flags", "metadata", "error",
    ]

    operations = []
    # Walk date subdirectories for .json files
    for root, _dirs, files in os.walk(log_payloads_dir):
        for filename in files:
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                print(
                    f"WARNING: Skipping malformed JSON in log_payloads: "
                    f"{os.path.relpath(filepath, hermes_home)} — {e}",
                    file=sys.stderr,
                )
                continue
            except OSError as e:
                print(
                    f"WARNING: Could not read log_payloads file: "
                    f"{os.path.relpath(filepath, hermes_home)} — {e}",
                    file=sys.stderr,
                )
                continue

            # Extract known fields, defaulting missing optional fields to None
            op = {}
            for field in KNOWN_FIELDS:
                op[field] = payload.get(field)

            # Compute result_size and drop result
            result = payload.get("result")
            if result is None or result == {}:
                op["result_size"] = 0
            else:
                try:
                    op["result_size"] = len(json.dumps(result))
                except (TypeError, ValueError):
                    op["result_size"] = 0

            # Track source file relative to log_payloads/
            op["source_file"] = os.path.relpath(filepath, log_payloads_dir)

            operations.append(op)

    return {"operations": operations, "available": True}


# ──────────────────────────────────────────────────────────────────────────────
# Step 9: Global Insights (Tasks 9.1 – 9.3)
# ──────────────────────────────────────────────────────────────────────────────

def compute_global_insights(sessions: list[dict]) -> dict:
    """
    Compute aggregate statistics across all sessions:
    totals, skills leaderboard, tools leaderboard.
    """
    total_sessions = len(sessions)
    total_messages = 0
    total_skill_loads = 0

    # Accumulators: skill_name -> {load_count, total_chars, token_estimate}
    skills_agg: dict[str, dict] = {}
    # Accumulators: tool_name -> count
    tools_agg: dict[str, int] = {}
    # Accumulators: command -> count (total / failed)
    cmd_agg: dict[str, int] = {}
    cmd_fail_agg: dict[str, int] = {}
    total_commands = 0
    failed_commands = 0

    for session in sessions:
        total_messages += session.get("message_count", 0)

        for skill in session.get("skills_loaded", []):
            total_skill_loads += 1
            name = skill.get("skill_name", "unknown")
            if name not in skills_agg:
                skills_agg[name] = {
                    "name": name,
                    "load_count": 0,
                    "total_chars": 0,
                    "token_estimate": 0,
                }
            skills_agg[name]["load_count"] += 1
            skills_agg[name]["total_chars"] += skill.get("content_chars", 0)
            skills_agg[name]["token_estimate"] += skill.get("token_estimate", 0)

        for tool in session.get("tool_calls", []):
            name = tool.get("tool_name", "unknown")
            tools_agg[name] = tools_agg.get(name, 0) + tool.get("count", 0)

        for cmd in session.get("shell_commands", []):
            total_commands += 1
            command = cmd.get("command", "")
            if command:
                cmd_agg[command] = cmd_agg.get(command, 0) + 1
            if cmd.get("exit_code") not in (0, None):
                failed_commands += 1
                if command:
                    cmd_fail_agg[command] = cmd_fail_agg.get(command, 0) + 1

    # Sort leaderboards by count descending
    skills_leaderboard = sorted(
        skills_agg.values(), key=lambda x: x["load_count"], reverse=True
    )
    tools_leaderboard = sorted(
        ({"name": k, "count": v} for k, v in tools_agg.items()),
        key=lambda x: x["count"],
        reverse=True,
    )
    most_executed = sorted(
        ({"command": k, "count": v} for k, v in cmd_agg.items()),
        key=lambda x: x["count"],
        reverse=True,
    )[:20]
    failed_list = sorted(
        ({"command": k, "failure_count": v} for k, v in cmd_fail_agg.items()),
        key=lambda x: x["failure_count"],
        reverse=True,
    )

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_skill_loads": total_skill_loads,
        "skills": skills_leaderboard,
        "tools": tools_leaderboard,
        "commands": {
            "total_commands": total_commands,
            "failed_commands": failed_commands,
            "most_executed_commands": most_executed,
            "failed_commands_list": failed_list,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Assembly & Output (Tasks 10.1 – 10.6)
# ──────────────────────────────────────────────────────────────────────────────

def _iso_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def assemble_snapshot(
    hermes_home: str, sessions: list[dict], global_insights: dict,
    log_payloads: dict | None = None,
) -> dict:
    """Build the final snapshot dict."""
    snapshot = {
        "generated_at": _iso_now(),
        "hermes_home": hermes_home,
        "sessions": sessions,
        "global_insights": global_insights,
    }
    if log_payloads is not None:
        snapshot["log_payloads"] = log_payloads
    else:
        snapshot["log_payloads"] = {"operations": [], "available": False}
    return snapshot


def write_local_snapshot(snapshot: dict, path: str = "snapshot_latest.json") -> str:
    """Write the snapshot to disk as formatted JSON."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"ERROR: Cannot write snapshot to {path}: {e}", file=sys.stderr)
        sys.exit(1)
    return path


def try_remote_push(snapshot: dict, remote_url: str, username: str | None = None) -> bool:
    """
    Attempt to POST the snapshot to a server.
    Includes the configured username in the POST body.
    Returns True on success, False on failure.
    """
    try:
        import requests  # noqa: F811 — optional dependency
    except ImportError:
        print(
            "ERROR: requests library required for remote mode. "
            "Install with: pip install requests",
            file=sys.stderr,
        )
        return False

    body = dict(snapshot)  # shallow copy to avoid mutating the original
    body["username"] = username or os.environ.get("USER", "local")

    endpoint = remote_url.rstrip("/") + "/api/snapshots"
    try:
        resp = requests.post(
            endpoint,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if 200 <= resp.status_code < 300:
            return True
        else:
            print(
                f"WARNING: Remote POST returned {resp.status_code}: {resp.text[:200]}",
                file=sys.stderr,
            )
            return False
    except requests.RequestException as e:
        print(f"WARNING: Remote POST failed: {e}", file=sys.stderr)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Main Pipeline
# ──────────────────────────────────────────────────────────────────────────────

def collect(hermes_home: str | None = None) -> dict:
    """
    Run the full collection pipeline.
    Returns the assembled snapshot dict.
    """
    if hermes_home is None:
        hermes_home = resolve_hermes_home()

    print(f"INFO: Using hermes_home={hermes_home}", file=sys.stderr)

    # Foundation
    db_path = validate_state_db(hermes_home)
    conn = open_db_readonly(db_path)

    try:
        # Step 1: Sessions
        sessions = extract_sessions(conn)
        if not sessions:
            print("INFO: No sessions found in state.db", file=sys.stderr)

        # Steps 2–7: Per-session enrichment
        error_map = parse_agent_log(hermes_home)

        for session in sessions:
            sid = session["id"]

            # Step 2: Skill loads
            skills = detect_skill_loads(conn, sid)

            # Step 3: Preceding user messages
            if skills:
                attach_preceding_user_messages(conn, skills, sid)

            # Step 4: Tool call aggregation
            tools = aggregate_tool_calls(conn, sid)

            # Step 4a: Shell command extraction
            shell_cmds = extract_shell_commands(conn, sid)

            # Step 5: Token estimation (redundant pass for safety)
            validate_token_estimates(skills)

            # Step 6: User messages
            user_msgs = extract_user_messages(conn, sid)

            # Step 7: Errors
            errors = error_map.get(sid, [])

            # Build the enriched session object matching the snapshot schema
            session["session_id"] = session.pop("id", sid)
            session["platform"] = session.pop("source", None)
            session["chat_name"] = session.pop("title", None)
            session["tokens"] = {
                "input": session.pop("input_tokens", 0),
                "output": session.pop("output_tokens", 0),
                "cache_read": session.pop("cache_read_tokens", 0),
                "cache_write": session.pop("cache_write_tokens", 0),
                "reasoning": session.pop("reasoning_tokens", 0),
                "estimated_cost_usd": session.pop("estimated_cost_usd", 0.0),
            }
            # Keep message_count and tool_call_count under stats
            session["stats"] = {
                "message_count": session.pop("message_count", 0),
                "tool_call_count": session.pop("tool_call_count", 0),
            }
            session["skills_loaded"] = skills
            session["tool_calls"] = tools
            session["shell_commands"] = shell_cmds
            session["user_messages"] = user_msgs
            session["errors"] = errors

            # Remove any leftover raw DB columns not in the snapshot schema
            for key in list(session.keys()):
                if key not in (
                    "session_id", "platform", "chat_name", "model",
                    "started_at", "ended_at", "ended_reason",
                    "tokens", "stats", "skills_loaded", "tool_calls",
                    "shell_commands", "user_messages", "errors",
                ):
                    del session[key]

        # Step 8: Log payloads extraction
        log_payloads = extract_log_payloads(hermes_home)

        # Global insights
        global_insights = compute_global_insights(sessions)

    finally:
        conn.close()

    return assemble_snapshot(hermes_home, sessions, global_insights, log_payloads)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hermes Analytics — Data Collector",
    )
    parser.add_argument(
        "--hermes-home",
        default=None,
        help="Path to Hermes data directory (default: $HERMES_HOME or ~/.hermes)",
    )
    parser.add_argument(
        "--output",
        default="snapshot_latest.json",
        help="Output path for the snapshot JSON (default: snapshot_latest.json)",
    )
    args = parser.parse_args()

    hermes_home = args.hermes_home or resolve_hermes_home()

    # Run the pipeline
    snapshot = collect(hermes_home=hermes_home)

    # Resolve username from env var → $USER → hostname
    username = (
        os.environ.get("HERMES_ANALYTICS_USER")
        or os.environ.get("USER")
        or os.uname().nodename
    )

    total_skills = sum(
        len(s.get("skills_loaded", [])) for s in snapshot["sessions"]
    )
    total_tools = sum(
        len(s.get("tool_calls", [])) for s in snapshot["sessions"]
    )
    total_log_payloads = len(snapshot.get("log_payloads", {}).get("operations", []))
    session_count = snapshot["global_insights"]["total_sessions"]

    # ── Push priority: local server → remote server → local file ──
    push_results: list[str] = []
    local_file_path = args.output

    # 1. Try local server (started by slash command)
    local_server_port = os.environ.get("HERMES_ANALYTICS_SERVER_PORT", "5555")
    local_url = f"http://localhost:{local_server_port}"
    if try_remote_push(snapshot, local_url, username=username):
        push_results.append(f"  Pushed to local server ({local_url})")
    else:
        push_results.append(f"  Local server unreachable at {local_url}")

    # 2. Try remote server (env var or hardcoded)
    remote_url = os.environ.get("HERMES_ANALYTICS_REMOTE")
    if remote_url:
        if try_remote_push(snapshot, remote_url, username=username):
            push_results.append(f"  Pushed to remote server ({remote_url})")
        else:
            push_results.append(f"  Remote server unreachable at {remote_url}")

    # 3. Always write local file as fallback
    local_path = write_local_snapshot(snapshot, local_file_path)
    push_results.append(f"  Saved locally ({local_path})")

    print(
        f"SUCCESS: Snapshot collected\n"
        f"  {session_count} sessions, {total_skills} skill loads, "
        f"{total_tools} tool types, {total_log_payloads} log payloads",
    )
    for result in push_results:
        print(result)


if __name__ == "__main__":
    main()
