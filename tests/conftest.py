"""
Shared pytest fixtures for Hermes Analytics tests.

Provides a synthetic state.db built programmatically with known data
so every test can assert against deterministic inputs.
"""

import json
import math
import os
import sqlite3
import tempfile

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Hermes DB schema helpers
# ──────────────────────────────────────────────────────────────────────────────

_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    model TEXT NOT NULL,
    started_at REAL,
    ended_at REAL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0.0,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0
);
"""

_MESSAGES_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    tool_call_id TEXT,
    timestamp REAL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""


def build_fixture_db(db_path: str) -> None:
    """Create a synthetic state.db with 3 sessions and realistic messages.

    Session layout:
      - id=1  telegram  2 skill loads, 5 tool calls, has errors, ~12 msgs
      - id=2  discord   0 skill loads, 8 tool calls, no errors, ~10 msgs
      - id=3  cli       1 skill load,  3 tool calls, has errors, ~8  msgs
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    # ── sessions table ────────────────────────────────────────────────
    cursor.execute(_SESSIONS_SCHEMA)
    cursor.execute(_MESSAGES_SCHEMA)

    sessions_data = [
        # id, source, model, started_at, ended_at, input_tokens, output_tokens,
        #   cache_read, cache_write, reasoning, cost, msg_count, tool_count
        (1, "telegram", "gpt-4o",
         1719312000.0, 1719312600.0,
         5000, 1200, 800, 0, 200, 0.04, 12, 5),
        (2, "discord", "claude-sonnet-4-20250514",
         1719315000.0, 1719315300.0,
         3000, 900, 0, 0, 0, 0.03, 10, 8),
        (3, "cli", "minimaxai/minimax-m2.7",
         1719318000.0, None,
         8000, 2500, 1500, 0, 400, 0.06, 8, 3),
    ]
    cursor.executemany(
        "INSERT INTO sessions (id, source, model, started_at, ended_at, "
        "input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, "
        "reasoning_tokens, estimated_cost_usd, message_count, tool_call_count) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        sessions_data,
    )

    # ── messages table ────────────────────────────────────────────────
    #
    # Session 1 (telegram): ~12 messages, 2 skill loads
    #   msg 1: user "Load the confluence skill"
    #   msg 2: assistant (skill_view -> confluence-skill, call-aaa)
    #   msg 3: tool (response: {"success":true,"name":"confluence-skill","path":"/memories/confluence-skill.md"})
    #   msg 4: user "Now load the github skill too"
    #   msg 5: assistant (skill_view -> github-skill, call-bbb)
    #   msg 6: tool (response: {"success":true,"name":"github-skill","path":"/memories/github-skill.md"})
    #   msg 7: user "Run a command"
    #   msg 8: assistant (terminal -> "ls -la", call-ccc)
    #   msg 9: tool ([terminal] ran `ls -la` -> exit 0)
    #   msg 10: assistant (browser_navigate -> url, call-ddd)
    #   msg 11: tool (browser response)
    #   msg 12: user "Navigate to another page"
    #   msg 13: assistant (browser_navigate -> url2, call-eee)
    #   msg 14: tool (browser response)

    # Session 2 (discord): ~10 messages, 0 skill loads, 8 tool calls
    #   msg 15: user "What's in this directory?"
    #   msg 16: assistant (terminal -> "find . -maxdepth 1", call-fff)
    #   msg 17: tool (response)
    #   msg 18: assistant (terminal -> "wc -l *.py", call-ggg)
    #   msg 19: tool (response)
    #   msg 20: assistant (terminal -> "cat README.md", call-hhh)
    #   msg 21: tool (response)
    #   msg 22: assistant (terminal -> "python -m pytest", call-iii)
    #   msg 23: tool (response)
    #   msg 24: assistant (browser_navigate -> url, call-jjj)
    #   msg 25: tool (response)
    #   msg 26: assistant (terminal -> "git status", call-kkk)
    #   msg 27: tool (response)
    #   msg 28: assistant (terminal -> "python server.py", call-lll)
    #   msg 29: tool (response)

    # Session 3 (cli): ~8 messages, 1 skill load
    #   msg 30: user "Load the brainstorming skill"
    #   msg 31: assistant (skill_view -> brainstorming, call-mmm)
    #   msg 32: tool (response: [skill_view] name=brainstorming (12,345 chars))
    #   msg 33: user "Open a browser"
    #   msg 34: assistant (browser_navigate -> url, call-nnn)
    #   msg 35: tool (response)
    #   msg 36: assistant (terminal -> "echo hello", call-ooo)
    #   msg 37: tool (response)

    messages_data = [
        # ── Session 1 ─────────────────────────────────────────────────
        # id, session_id, role, content, tool_calls, tool_name, tool_call_id, timestamp
        (1, 1, "user", "Load the confluence skill for me", None, None, None, 1719312010.0),
        (2, 1, "assistant", None,
         json.dumps([
             {"id": "call-aaa", "type": "function",
              "function": {"name": "skill_view", "arguments": '{"name":"confluence-skill"}'}}
         ]),
         None, None, 1719312020.0),
        (3, 1, "tool",
         json.dumps({"success": True, "name": "confluence-skill",
                      "path": "/memories/confluence-skill.md"}),
         None, "skill_view", "call-aaa", 1719312030.0),
        (4, 1, "user", "Now load the github-skill too", None, None, None, 1719312040.0),
        (5, 1, "assistant", None,
         json.dumps([
             {"id": "call-bbb", "type": "function",
              "function": {"name": "skill_view", "arguments": '{"name":"github-skill"}'}}
         ]),
         None, None, 1719312050.0),
        (6, 1, "tool",
         json.dumps({"success": True, "name": "github-skill",
                      "path": "/memories/github-skill.md"}),
         None, "skill_view", "call-bbb", 1719312060.0),
        (7, 1, "user", "Run a terminal command to list files", None, None, None, 1719312070.0),
        (8, 1, "assistant", None,
         json.dumps([
             {"id": "call-ccc", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"ls -la"}'}}
         ]),
         None, None, 1719312080.0),
        (9, 1, "tool", "[terminal] ran `ls -la` -> exit 0, 3 lines output",
         None, "terminal", "call-ccc", 1719312090.0),
        # Assistant + tool for browser_navigate call-ddd
        (10, 1, "assistant", None,
         json.dumps([
             {"id": "call-ddd", "type": "function",
              "function": {"name": "browser_navigate", "arguments": '{"url":"https://example.com"}'}}
         ]),
         None, None, 1719312100.0),
        (11, 1, "tool", "Navigated to https://example.com",
         None, "browser_navigate", "call-ddd", 1719312110.0),
        # Second browser_navigate call
        (12, 1, "user", "Navigate to another page now", None, None, None, 1719312120.0),
        (13, 1, "assistant", None,
         json.dumps([
             {"id": "call-eee", "type": "function",
              "function": {"name": "browser_navigate", "arguments": '{"url":"https://other.example.com"}'}}
         ]),
         None, None, 1719312130.0),
        (14, 1, "tool", "Navigated to https://other.example.com",
         None, "browser_navigate", "call-eee", 1719312140.0),

        # ── Session 2 ─────────────────────────────────────────────────
        (15, 2, "user", "What's in this directory? Show me everything", None, None, None, 1719315010.0),
        # Tool calls (8 total for session 2)
        (16, 2, "assistant", None,
         json.dumps([
             {"id": "call-fff", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"find . -maxdepth 1"}'}}
         ]),
         None, None, 1719315020.0),
        (17, 2, "tool", "[terminal] ran `find . -maxdepth 1` -> exit 0, 15 lines output",
         None, "terminal", "call-fff", 1719315030.0),
        (18, 2, "assistant", None,
         json.dumps([
             {"id": "call-ggg", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"wc -l *.py"}'}}
         ]),
         None, None, 1719315040.0),
        (19, 2, "tool", "[terminal] ran `wc -l *.py` -> exit 0, 5 lines output",
         None, "terminal", "call-ggg", 1719315050.0),
        (20, 2, "assistant", None,
         json.dumps([
             {"id": "call-hhh", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"cat README.md"}'}}
         ]),
         None, None, 1719315060.0),
        (21, 2, "tool", "[terminal] ran `cat README.md` -> exit 0, 42 lines output",
         None, "terminal", "call-hhh", 1719315070.0),
        (22, 2, "assistant", None,
         json.dumps([
             {"id": "call-iii", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"python -m pytest"}'}}
         ]),
         None, None, 1719315080.0),
        (23, 2, "tool", "[terminal] ran `python -m pytest` -> exit 1, 20 lines output",
         None, "terminal", "call-iii", 1719315090.0),
        (24, 2, "assistant", None,
         json.dumps([
             {"id": "call-jjj", "type": "function",
              "function": {"name": "browser_navigate", "arguments": '{"url":"https://docs.pytest.org"}'}}
         ]),
         None, None, 1719315100.0),
        (25, 2, "tool", "Navigated to https://docs.pytest.org",
         None, "browser_navigate", "call-jjj", 1719315110.0),
        (26, 2, "assistant", None,
         json.dumps([
             {"id": "call-kkk", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"git status"}'}}
         ]),
         None, None, 1719315120.0),
        (27, 2, "tool", "[terminal] ran `git status` -> exit 0, 8 lines output",
         None, "terminal", "call-kkk", 1719315130.0),
        (28, 2, "assistant", None,
         json.dumps([
             {"id": "call-lll", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"python server.py"}'}}
         ]),
         None, None, 1719315140.0),
        (29, 2, "tool", "[terminal] ran `python server.py` -> exit 0, 10 lines output",
         None, "terminal", "call-lll", 1719315150.0),

        # ── Session 3 ─────────────────────────────────────────────────
        (30, 3, "user", "Load the brainstorming skill", None, None, None, 1719318010.0),
        (31, 3, "assistant", None,
         json.dumps([
             {"id": "call-mmm", "type": "function",
              "function": {"name": "skill_view", "arguments": '{"name":"brainstorming"}'}}
         ]),
         None, None, 1719318020.0),
        (32, 3, "tool",
         "[skill_view] name=brainstorming (12,345 chars)",
         None, "skill_view", "call-mmm", 1719318030.0),
        (33, 3, "user", "Open a browser and navigate somewhere", None, None, None, 1719318040.0),
        (34, 3, "assistant", None,
         json.dumps([
             {"id": "call-nnn", "type": "function",
              "function": {"name": "browser_navigate", "arguments": '{"url":"https://github.com"}'}}
         ]),
         None, None, 1719318050.0),
        (35, 3, "tool", "Navigated to https://github.com",
         None, "browser_navigate", "call-nnn", 1719318060.0),
        (36, 3, "assistant", None,
         json.dumps([
             {"id": "call-ooo", "type": "function",
              "function": {"name": "terminal", "arguments": '{"command":"echo hello"}'}}
         ]),
         None, None, 1719318070.0),
        (37, 3, "tool", "[terminal] ran `echo hello` -> exit 0, 1 lines output",
         None, "terminal", "call-ooo", 1719318080.0),
    ]

    cursor.executemany(
        "INSERT INTO messages (id, session_id, role, content, tool_calls, "
        "tool_name, tool_call_id, timestamp) VALUES (?,?,?,?,?,?,?,?)",
        messages_data,
    )

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# Pytest fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Create a temporary HERMES_HOME with a synthetic state.db."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    db_path = str(hermes_home / "state.db")
    build_fixture_db(db_path)
    return str(hermes_home)


@pytest.fixture
def db_path(tmp_hermes_home):
    """Return the path to the synthetic state.db."""
    return os.path.join(tmp_hermes_home, "state.db")


@pytest.fixture
def create_agent_log(tmp_hermes_home):
    """Create a logs/agent.log with error lines for sessions 1 and 3."""
    logs_dir = os.path.join(tmp_hermes_home, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "agent.log")
    with open(log_path, "w") as f:
        f.write("[session_1] 2024-06-25 12:00:01,234 Tool terminal returned error (63.59s)\n")
        f.write("[session_3] 2024-06-25 14:30:45,678 Tool terminal returned error (12.34s)\n")
    return log_path


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot fixture (runs the collector against the fixture DB)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def snapshot(tmp_hermes_home, monkeypatch, create_agent_log):
    """Run the collector against the fixture DB and return the snapshot dict."""
    monkeypatch.setenv("HERMES_HOME", tmp_hermes_home)
    # Import here to avoid import-time side effects
    from userend.collector import collect
    return collect(hermes_home=tmp_hermes_home)
