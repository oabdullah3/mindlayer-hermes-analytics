"""
API tests — verify all REST endpoints for the local single-user server.
"""

import json
import os
from unittest import mock

import pytest
import server


@pytest.fixture
def client():
    """Flask test client."""
    server.app.config["TESTING"] = True
    return server.app.test_client()


@pytest.fixture
def sample_snapshot():
    """A minimal valid snapshot for testing."""
    return {
        "generated_at": "2026-06-25T12:00:00Z",
        "hermes_home": "/tmp/test-hermes",
        "sessions": [
            {
                "session_id": "101",
                "platform": "cli",
                "model": "test-model",
                "started_at": 1719312000.0,
                "ended_at": None,
                "chat_name": None,
                "tokens": {
                    "input": 100,
                    "output": 50,
                    "cache_read": 0,
                    "cache_write": 0,
                    "reasoning": 0,
                    "estimated_cost_usd": 0.0,
                },
                "stats": {"message_count": 5, "tool_call_count": 2},
                "skills_loaded": [
                    {
                        "skill_name": "test-skill",
                        "load_message_id": 1,
                        "load_timestamp": 1719312100.0,
                        "preceding_user_message": "load test-skill",
                        "tool_call_id": "call-test",
                        "content_chars": 100,
                        "token_estimate": 25,
                    }
                ],
                "tool_calls": [
                    {"tool_name": "terminal", "count": 2, "message_ids": [3, 5]}
                ],
                "shell_commands": [],
                "user_messages": [
                    {"message_id": 2, "content": "hello", "timestamp": 1719312050.0}
                ],
                "errors": [],
            }
        ],
        "global_insights": {
            "total_sessions": 1,
            "total_messages": 1,
            "total_skill_loads": 1,
            "skills": [{"name": "test-skill", "load_count": 1, "total_chars": 100, "token_estimate": 25}],
            "tools": [{"name": "terminal", "count": 2}],
            "commands": {
                "total_commands": 0,
                "failed_commands": 0,
                "most_executed_commands": [],
                "failed_commands_list": [],
            },
        },
    }


def _mock_snapshot(monkeypatch, snapshot):
    """Helper: monkeypatch _load_snapshot to return the given snapshot."""
    monkeypatch.setattr(server, "_load_snapshot", lambda: snapshot)


# ── Health ─────────────────────────────────────────────────────────


class TestHealth:
    def test_health_ok(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["total_sessions"] == 1

    def test_health_no_snapshot(self, client, monkeypatch):
        monkeypatch.setattr(server, "_load_snapshot", lambda: None)
        resp = client.get("/api/health")
        assert resp.status_code == 503
        assert resp.get_json()["status"] == "error"


# ── Snapshots ───────────────────────────────────────────────────────


class TestSnapshots:
    def test_snapshots_latest(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/snapshots/latest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["hermes_home"] == "/tmp/test-hermes"
        assert len(data["sessions"]) == 1

    def test_snapshots_latest_no_data(self, client, monkeypatch):
        monkeypatch.setattr(server, "_load_snapshot", lambda: None)
        resp = client.get("/api/snapshots/latest")
        assert resp.status_code == 503


# ── Skills ──────────────────────────────────────────────────────────


class TestSkills:
    def test_skills_list(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "test-skill"
        assert data[0]["load_count"] == 1

    def test_skills_detail_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/skills/test-skill")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skill_name"] == "test-skill"
        assert len(data["sessions"]) == 1

    def test_skills_detail_not_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/skills/nonexistent")
        assert resp.status_code == 404


# ── Tools ───────────────────────────────────────────────────────────


class TestTools:
    def test_tools_list(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "terminal"

    def test_tools_detail_not_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/tools/nonexistent")
        assert resp.status_code == 404


# ── Sessions ────────────────────────────────────────────────────────


class TestSessions:
    def test_sessions_list(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["session_id"] == "101"

    def test_sessions_detail_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/sessions/101")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["session_id"] == "101"
        assert "skills_loaded" in data

    def test_sessions_detail_not_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404


# ── Snapshot POST ───────────────────────────────────────────────────


class TestSnapshotPost:
    def test_post_snapshot_valid(self, client, sample_snapshot, monkeypatch, tmp_path):
        monkeypatch.setattr(server, "_SNAPSHOT_PATH", str(tmp_path / "snapshot_latest.json"))

        resp = client.post(
            "/api/snapshots",
            data=json.dumps(sample_snapshot),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["sessions"] == 1

        # Verify file was written to disk
        assert os.path.isfile(tmp_path / "snapshot_latest.json")
        with open(tmp_path / "snapshot_latest.json") as f:
            saved = json.load(f)
        assert len(saved["sessions"]) == 1

    def test_post_snapshot_missing_fields(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(server, "_SNAPSHOT_PATH", str(tmp_path / "snapshot_latest.json"))

        resp = client.post(
            "/api/snapshots",
            data=json.dumps({"some": "data"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "sessions" in resp.get_json()["error"].lower()

    def test_post_snapshot_invalid_json(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(server, "_SNAPSHOT_PATH", str(tmp_path / "snapshot_latest.json"))

        resp = client.post(
            "/api/snapshots",
            data="not valid json {{{",
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── Refresh ─────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_endpoint(self, client, sample_snapshot, monkeypatch):
        _mock_snapshot(monkeypatch, sample_snapshot)

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with mock.patch("server.subprocess.run", return_value=mock_result):
            resp = client.post("/api/refresh")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "ok"
