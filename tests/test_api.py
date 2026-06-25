"""
API tests — verify all REST endpoints for the multi-user server (ADR-0002).
"""

import json
import os
from unittest import mock

import pytest
import remoteend.server as server


@pytest.fixture
def client():
    """Flask test client with the app configured for testing."""
    server.app.config["TESTING"] = True
    return server.app.test_client()


@pytest.fixture
def sample_snapshot():
    """A minimal valid snapshot for testing API ingestion."""
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


def _mock_snapshots(sample_snapshot, monkeypatch):
    """Helper: monkeypatch get_all_latest_snapshots to return one user."""
    monkeypatch.setattr(
        server,
        "get_all_latest_snapshots",
        lambda: {"testuser": sample_snapshot},
    )


# ── Health ─────────────────────────────────────────────────────────


class TestHealth:
    def test_health_ok(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["users"] == 1
        assert data["total_sessions"] == 1

    def test_health_no_snapshot(self, client, monkeypatch):
        monkeypatch.setattr(server, "get_all_latest_snapshots", lambda: {})
        resp = client.get("/api/health")
        assert resp.status_code == 503
        assert resp.get_json()["status"] == "error"


# ── Snapshots ───────────────────────────────────────────────────────


class TestSnapshots:
    def test_snapshots_latest(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/snapshots/latest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "users" in data
        assert "snapshots" in data
        assert "testuser" in data["snapshots"]


# ── Skills ──────────────────────────────────────────────────────────


class TestSkills:
    def test_skills_list(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["skill_name"] == "test-skill"
        assert data[0]["total_loads"] == 1

    def test_skills_detail_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/skills/test-skill")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skill_name"] == "test-skill"
        assert len(data["sessions"]) == 1

    def test_skills_detail_not_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/skills/nonexistent")
        assert resp.status_code == 404


# ── Tools ────────────────────────────────────────────────────────────


class TestTools:
    def test_tools_list(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["tool_name"] == "terminal"

    def test_tools_detail_not_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/tools/nonexistent")
        assert resp.status_code == 404


# ── Sessions ─────────────────────────────────────────────────────────


class TestSessions:
    def test_sessions_list(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["session_id"] == "101"

    def test_sessions_detail_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/sessions/101")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["session_id"] == "101"
        assert "skills_loaded" in data

    def test_sessions_detail_not_found(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404


# ── Multi-user endpoints ────────────────────────────────────────────


class TestUsers:
    def test_users_list(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/users")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["username"] == "testuser"

    def test_user_latest(self, client, sample_snapshot, monkeypatch):
        monkeypatch.setattr(
            server,
            "get_snapshot_for_user",
            lambda username: sample_snapshot if username == "testuser" else None,
        )
        resp = client.get("/api/users/testuser/latest")
        assert resp.status_code == 200
        assert resp.get_json() == sample_snapshot

    def test_user_latest_not_found(self, client, monkeypatch):
        monkeypatch.setattr(server, "get_snapshot_for_user", lambda u: None)
        monkeypatch.setattr(server, "get_all_latest_snapshots", lambda: {})
        resp = client.get("/api/users/bob/latest")
        assert resp.status_code == 404


# ── Leaderboard ──────────────────────────────────────────────────────


class TestLeaderboard:
    def test_leaderboard_sessions(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/leaderboard/sessions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["username"] == "testuser"
        assert data[0]["total_sessions"] == 1

    def test_leaderboard_skills(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/leaderboard/skills")
        assert resp.status_code == 200
        assert resp.get_json()[0]["total_skill_loads"] == 1

    def test_leaderboard_tools(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/leaderboard/tools")
        assert resp.status_code == 200
        assert resp.get_json()[0]["total_tool_calls"] == 1


# ── Snapshot POST ────────────────────────────────────────────────────


class TestSnapshotPost:
    def test_post_snapshot_valid(self, client, sample_snapshot, monkeypatch, tmp_path):
        monkeypatch.setattr(server, "SERVER_DATA", str(tmp_path / "server_data"))
        monkeypatch.setattr(server, "get_all_latest_snapshots", lambda: {})

        body = dict(sample_snapshot)
        body["username"] = "alice"

        resp = client.post(
            "/api/snapshots",
            data=json.dumps(body),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "accepted"

        # Verify file was created on disk
        user_dir = tmp_path / "server_data" / "alice"
        assert user_dir.is_dir()
        snapshots = list(user_dir.glob("snapshot_*.json"))
        assert len(snapshots) == 1

    def test_post_snapshot_missing_username(self, client, sample_snapshot, monkeypatch):
        monkeypatch.setattr(server, "get_all_latest_snapshots", lambda: {})
        resp = client.post(
            "/api/snapshots",
            data=json.dumps(sample_snapshot),
            content_type="application/json",
        )
        assert resp.status_code == 422

    def test_post_snapshot_invalid_json(self, client, monkeypatch):
        monkeypatch.setattr(server, "get_all_latest_snapshots", lambda: {})
        resp = client.post(
            "/api/snapshots",
            data="not valid json {{{",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_post_snapshot_missing_fields(self, client, monkeypatch):
        monkeypatch.setattr(server, "get_all_latest_snapshots", lambda: {})
        resp = client.post(
            "/api/snapshots",
            data=json.dumps({"username": "alice", "some": "data"}),
            content_type="application/json",
        )
        assert resp.status_code == 422
        assert "sessions" in resp.get_json()["error"].lower()


# ── Refresh ──────────────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_endpoint(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)

        mock_result = mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with mock.patch("remoteend.server.subprocess.run", return_value=mock_result):
            resp = client.post("/api/refresh")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "refreshed"


# ── Username query parameter ─────────────────────────────────────────


class TestUsernameFilter:
    def test_sessions_filtered_by_username(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/sessions?username=testuser")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_sessions_wrong_username_empty(self, client, sample_snapshot, monkeypatch):
        _mock_snapshots(sample_snapshot, monkeypatch)
        resp = client.get("/api/sessions?username=nonexistent")
        assert resp.status_code == 200
        assert resp.get_json() == []
