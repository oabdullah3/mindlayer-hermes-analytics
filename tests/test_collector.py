"""
Collector tests — verify all extraction steps against the synthetic fixture.
"""

import json
import math


class TestCollector:
    """Tests for the collector pipeline against the fixture database."""

    def test_session_count(self, snapshot):
        """1.2 — collector extracts exactly 3 sessions."""
        sessions = snapshot["sessions"]
        assert len(sessions) == 3

    def test_session_metadata(self, snapshot):
        """1.3 — each session has correct platform, model, tokens."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}

        # Session 1 — telegram
        s1 = sessions[1]
        assert s1["platform"] == "telegram"
        assert s1["model"] == "gpt-4o"
        assert s1["tokens"]["input"] == 5000
        assert s1["tokens"]["output"] == 1200
        assert s1["tokens"]["cache_read"] == 800
        assert s1["tokens"]["reasoning"] == 200
        assert s1["stats"]["message_count"] == 12
        assert s1["stats"]["tool_call_count"] == 5

        # Session 2 — discord
        s2 = sessions[2]
        assert s2["platform"] == "discord"
        assert s2["model"] == "claude-sonnet-4-20250514"
        assert s2["tokens"]["input"] == 3000
        assert s2["tokens"]["output"] == 900
        assert s2["stats"]["message_count"] == 10
        assert s2["stats"]["tool_call_count"] == 8

        # Session 3 — cli
        s3 = sessions[3]
        assert s3["platform"] == "cli"
        assert s3["model"] == "minimaxai/minimax-m2.7"
        assert s3["tokens"]["input"] == 8000
        assert s3["tokens"]["output"] == 2500
        assert s3["tokens"]["cache_read"] == 1500
        assert s3["tokens"]["reasoning"] == 400
        assert s3["stats"]["message_count"] == 8
        assert s3["stats"]["tool_call_count"] == 3

    def test_skill_load_detection(self, snapshot):
        """1.4 — session 1 has 2 skills, session 2 has 0, session 3 has 1."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}

        assert len(sessions[1]["skills_loaded"]) == 2
        assert len(sessions[2]["skills_loaded"]) == 0
        assert len(sessions[3]["skills_loaded"]) == 1

    def test_skill_names_parsed(self, snapshot):
        """1.5 — skill names extracted from tool response content match fixture."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}

        skill_names_s1 = sorted(
            sl["skill_name"] for sl in sessions[1]["skills_loaded"]
        )
        assert skill_names_s1 == ["confluence-skill", "github-skill"]

        skill_names_s3 = [sl["skill_name"] for sl in sessions[3]["skills_loaded"]]
        assert skill_names_s3 == ["brainstorming"]

    def test_preceding_user_message(self, snapshot):
        """1.6 — each skill load has non-null preceding_user_message."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}

        # Session 1: skill loads should have preceding user messages
        for sl in sessions[1]["skills_loaded"]:
            assert sl["preceding_user_message"] is not None, (
                f"Skill {sl['skill_name']} missing preceding_user_message"
            )
            if sl["skill_name"] == "confluence-skill":
                assert sl["preceding_user_message"] == "Load the confluence skill for me"
            elif sl["skill_name"] == "github-skill":
                assert sl["preceding_user_message"] == "Now load the github-skill too"

        # Session 3: brainstorming skill
        for sl in sessions[3]["skills_loaded"]:
            assert sl["preceding_user_message"] is not None
            assert sl["preceding_user_message"] == "Load the brainstorming skill"

    def test_tool_call_aggregation(self, snapshot):
        """1.7 — tool calls aggregated with correct counts per tool_name."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}

        # Session 1: skill_view(2), terminal(1), browser_navigate(2) = 3 tool types
        s1_tools = {t["tool_name"]: t for t in sessions[1]["tool_calls"]}
        assert len(s1_tools) >= 3
        assert s1_tools["skill_view"]["count"] == 2
        assert s1_tools["terminal"]["count"] == 1
        assert s1_tools["browser_navigate"]["count"] == 2
        # message_ids length should match count
        assert len(s1_tools["skill_view"]["message_ids"]) == 2

        # Session 2: terminal(6), browser_navigate(1) = 2 tool types
        s2_tools = {t["tool_name"]: t for t in sessions[2]["tool_calls"]}
        assert s2_tools["terminal"]["count"] == 6
        assert s2_tools["browser_navigate"]["count"] == 1

        # Session 3: skill_view(1), browser_navigate(1), terminal(1)
        s3_tools = {t["tool_name"]: t for t in sessions[3]["tool_calls"]}
        assert len(s3_tools) >= 3
        assert s3_tools["skill_view"]["count"] == 1
        assert s3_tools["browser_navigate"]["count"] == 1
        assert s3_tools["terminal"]["count"] == 1

    def test_token_estimation(self, snapshot):
        """1.8 — token_estimate = CEIL(content_chars / 4) for each skill load."""
        for session in snapshot["sessions"]:
            for sl in session.get("skills_loaded", []):
                expected = math.ceil(sl["content_chars"] / 4) if sl["content_chars"] > 0 else 0
                assert sl["token_estimate"] == expected, (
                    f"token_estimate {sl['token_estimate']} != "
                    f"CEIL({sl['content_chars']}/4) = {expected} "
                    f"for skill {sl['skill_name']}"
                )

    def test_user_messages_collected(self, snapshot):
        """1.9 — each session has correct number of user_messages."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}

        # Session 1: 4 user messages (ids 1, 4, 7, 12)
        assert len(sessions[1]["user_messages"]) == 4

        # Session 2: 1 user message
        assert len(sessions[2]["user_messages"]) == 1

        # Session 3: 2 user messages
        assert len(sessions[3]["user_messages"]) == 2

    def test_global_insights(self, snapshot):
        """1.10 — global_insights has correct totals and sorted leaderboards."""
        gi = snapshot["global_insights"]

        assert gi["total_sessions"] == 3
        assert gi["total_skill_loads"] == 3
        # Skills leaderboard sorted by load_count desc
        skills = gi["skills"]
        assert len(skills) >= 3
        for i in range(len(skills) - 1):
            assert skills[i]["load_count"] >= skills[i + 1]["load_count"], (
                "Skills leaderboard not sorted by load_count desc"
            )

        # Tools leaderboard sorted by count desc
        tools = gi["tools"]
        assert len(tools) >= 3
        for i in range(len(tools) - 1):
            assert tools[i]["count"] >= tools[i + 1]["count"], (
                "Tools leaderboard not sorted by count desc"
            )

    def test_missing_optional_sources(self, tmp_hermes_home, monkeypatch):
        """1.11 — collector completes without crash when agent.log missing."""
        # Remove the agent.log if it exists (from create_agent_log fixture)
        import os
        log_path = os.path.join(tmp_hermes_home, "logs", "agent.log")
        if os.path.exists(log_path):
            os.remove(log_path)

        monkeypatch.setenv("HERMES_HOME", tmp_hermes_home)
        from collector import collect
        snapshot = collect(hermes_home=tmp_hermes_home)

        # Should complete successfully
        assert snapshot is not None
        assert len(snapshot["sessions"]) == 3
        # All sessions should have empty errors
        for session in snapshot["sessions"]:
            assert session["errors"] == []

    def test_error_parsing(self, snapshot):
        """1.12 — when agent.log exists, errors correctly associated."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}

        # Session 1 should have 1 error
        assert len(sessions[1]["errors"]) == 1
        assert sessions[1]["errors"][0]["session_id"] == 1
        assert sessions[1]["errors"][0]["duration_s"] == 63.59

        # Session 2 should have no errors
        assert len(sessions[2]["errors"]) == 0

        # Session 3 should have 1 error
        assert len(sessions[3]["errors"]) == 1
        assert sessions[3]["errors"][0]["session_id"] == 3
        assert sessions[3]["errors"][0]["duration_s"] == 12.34
