"""
Schema tests — validate that generated snapshots conform to the documented JSON schema.
"""

import re


class TestTopLevel:
    def test_top_level_keys(self, snapshot):
        """5.2 — snapshot has generated_at, hermes_home, sessions, global_insights."""
        assert "generated_at" in snapshot
        assert "hermes_home" in snapshot
        assert "sessions" in snapshot
        assert "global_insights" in snapshot

    def test_generated_at_format(self, snapshot):
        """5.3 — generated_at matches ISO 8601 UTC pattern."""
        ga = snapshot["generated_at"]
        assert isinstance(ga, str)
        # ISO 8601: YYYY-MM-DDTHH:MM:SS(.microseconds)?(+/-offset|Z)
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(pattern, ga), f"generated_at '{ga}' does not match ISO 8601"
        # Should have timezone info (either +00:00 or Z)
        assert "+" in ga or ga.endswith("Z") or "z" in ga.lower(), (
            f"generated_at '{ga}' missing timezone"
        )


class TestSessionStructure:
    def test_session_object_structure(self, snapshot):
        """5.4 — each session has all required keys with correct types."""
        required_keys = {
            "session_id": int,
            "platform": str,
            "model": str,
            "started_at": (int, float),
            "tokens": dict,
            "stats": dict,
            "skills_loaded": list,
            "tool_calls": list,
            "user_messages": list,
            "errors": list,
        }

        for session in snapshot["sessions"]:
            for key, expected_type in required_keys.items():
                assert key in session, f"Missing key '{key}' in session {session.get('session_id')}"
                value = session[key]
                if isinstance(expected_type, tuple):
                    assert isinstance(value, expected_type), (
                        f"Key '{key}' has type {type(value).__name__}, "
                        f"expected one of {[t.__name__ for t in expected_type]}"
                    )
                else:
                    assert isinstance(value, expected_type), (
                        f"Key '{key}' has type {type(value).__name__}, "
                        f"expected {expected_type.__name__}"
                    )

            # Check tokens sub-keys
            tokens = session["tokens"]
            for token_key in ("input", "output", "cache_read", "cache_write",
                              "reasoning", "estimated_cost_usd"):
                assert token_key in tokens, (
                    f"Missing token key '{token_key}' in session {session['session_id']}"
                )

            # Check stats sub-keys
            stats = session["stats"]
            for stat_key in ("message_count", "tool_call_count"):
                assert stat_key in stats, (
                    f"Missing stats key '{stat_key}' in session {session['session_id']}"
                )
                assert isinstance(stats[stat_key], int)

    def test_empty_arrays_for_blank_sessions(self, snapshot):
        """5.5 — session with no skills has empty lists, not null."""
        sessions = {s["session_id"]: s for s in snapshot["sessions"]}
        session_2 = sessions[2]

        assert session_2["skills_loaded"] == []
        assert session_2["tool_calls"] != []  # session 2 has tools
        assert session_2["errors"] == []

        # Ensure they are lists (not None)
        assert isinstance(session_2["skills_loaded"], list)
        assert isinstance(session_2["errors"], list)


class TestGlobalInsights:
    def test_global_insights_structure(self, snapshot):
        """5.6 — global_insights has correct keys and types."""
        gi = snapshot["global_insights"]

        required_keys = {
            "total_sessions": int,
            "total_messages": int,
            "total_skill_loads": int,
            "skills": list,
            "tools": list,
        }

        for key, expected_type in required_keys.items():
            assert key in gi, f"Missing key '{key}' in global_insights"
            assert isinstance(gi[key], expected_type), (
                f"Key '{key}' has type {type(gi[key]).__name__}, "
                f"expected {expected_type.__name__}"
            )

        # Totals must be non-negative
        assert gi["total_sessions"] >= 0
        assert gi["total_messages"] >= 0
        assert gi["total_skill_loads"] >= 0


class TestSkillLoadStructure:
    def test_skill_load_object_structure(self, snapshot):
        """5.7 — each skills_loaded entry has all required fields."""
        required_keys = {
            "skill_name": str,
            "load_message_id": int,
            "load_timestamp": (int, float),
            "preceding_user_message": (str, type(None)),
            "tool_call_id": str,
            "content_chars": int,
            "token_estimate": int,
        }

        for session in snapshot["sessions"]:
            for sl in session.get("skills_loaded", []):
                for key, expected_type in required_keys.items():
                    assert key in sl, (
                        f"Missing key '{key}' in skill load for "
                        f"session {session['session_id']}"
                    )
                    value = sl[key]
                    if isinstance(expected_type, tuple):
                        assert isinstance(value, expected_type), (
                            f"Key '{key}' has type {type(value).__name__}, "
                            f"expected one of {[t.__name__ for t in expected_type]}"
                        )
                    else:
                        assert isinstance(value, expected_type), (
                            f"Key '{key}' has type {type(value).__name__}, "
                            f"expected {expected_type.__name__}"
                        )

                # content_chars and token_estimate must be non-negative
                assert sl["content_chars"] >= 0
                assert sl["token_estimate"] >= 0


class TestToolCallStructure:
    def test_tool_call_object_structure(self, snapshot):
        """5.8 — each tool_calls entry has tool_name, count, message_ids."""
        for session in snapshot["sessions"]:
            for tc in session.get("tool_calls", []):
                assert "tool_name" in tc, (
                    f"Missing tool_name in session {session['session_id']}"
                )
                assert isinstance(tc["tool_name"], str)

                assert "count" in tc, (
                    f"Missing count in session {session['session_id']}"
                )
                assert isinstance(tc["count"], int)
                assert tc["count"] > 0

                assert "message_ids" in tc, (
                    f"Missing message_ids in session {session['session_id']}"
                )
                assert isinstance(tc["message_ids"], list)
                # message_ids length should match count
                assert len(tc["message_ids"]) == tc["count"], (
                    f"message_ids length {len(tc['message_ids'])} != count "
                    f"{tc['count']} for tool {tc['tool_name']}"
                )
                for mid in tc["message_ids"]:
                    assert isinstance(mid, int)
