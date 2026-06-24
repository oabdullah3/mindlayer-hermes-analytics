## 1. Test Infrastructure Setup

- [ ] 1.1 Create `tests/` directory with `__init__.py`
- [ ] 1.2 Add `pytest` to `requirements.txt`
- [ ] 1.3 Create `tests/conftest.py` with `tmp_hermes_home` fixture that creates a temp directory for the synthetic state.db
- [ ] 1.4 Create `db_path` fixture that returns the path to the synthetic state.db (built on demand)

## 2. Synthetic Test Fixture (state.db)

- [ ] 2.1 Implement `build_fixture_db(path)` function in conftest.py that creates a state.db with Hermes schema
- [ ] 2.2 Create `sessions` table and insert 3 sessions: telegram (id=1, has skills/tools/errors/tokens), discord (id=2, no skills, many tools, no errors), cli (id=3, 1 skill, few tools, has errors)
- [ ] 2.3 Create `messages` table and insert user messages, assistant messages with `tool_calls` JSON (skill_view), and tool response messages linked by tool_call_id
- [ ] 2.4 Insert messages across all 3 sessions: ~12 messages in session 1, ~10 in session 2, ~8 in session 3
- [ ] 2.5 Ensure at least 2 skill loads (skill_view) exist with preceding user messages
- [ ] 2.6 Ensure at least 3 distinct tool_names appear (skill_view, terminal, browser_navigate)
- [ ] 2.7 Populate session token columns (input_tokens, output_tokens, cache_read_tokens, reasoning_tokens, estimated_cost_usd) with non-zero values
- [ ] 2.8 Set `message_count` and `tool_call_count` on sessions to match actual inserted data
- [ ] 2.9 Add a `create_agent_log` fixture that creates `logs/agent.log` with 2 error lines for sessions 1 and 3

## 3. Collector Tests

- [ ] 3.1 Create `tests/test_collector.py` with import of collector module
- [ ] 3.2 Test: `test_session_count` — collector extracts exactly 3 sessions
- [ ] 3.3 Test: `test_session_metadata` — each session has correct platform, model, tokens matching fixture
- [ ] 3.4 Test: `test_skill_load_detection` — session 1 has 2 skills, session 2 has 0, session 3 has 1
- [ ] 3.5 Test: `test_skill_names_parsed` — skill names extracted from tool response content match fixture
- [ ] 3.6 Test: `test_preceding_user_message` — each skill load has non-null preceding_user_message matching the fixture user message
- [ ] 3.7 Test: `test_tool_call_aggregation` — session 1 tool_calls list has correct counts per tool_name
- [ ] 3.8 Test: `test_token_estimation` — token_estimate = CEIL(content_chars / 4) for each skill load
- [ ] 3.9 Test: `test_user_messages_collected` — each session has correct number of user_messages entries
- [ ] 3.10 Test: `test_global_insights` — total_sessions=3, total_skill_loads=3, skills/tools leaderboards sorted by count
- [ ] 3.11 Test: `test_missing_optional_sources` — collector completes without crash when agent.log missing
- [ ] 3.12 Test: `test_error_parsing` — when agent.log exists, errors are correctly associated with sessions 1 and 3

## 4. API Tests

- [ ] 4.1 Create `tests/test_api.py` with Flask test client setup using a fixture snapshot
- [ ] 4.2 Test: `test_health_ok` — GET /api/health returns 200 with status ok when snapshot loaded
- [ ] 4.3 Test: `test_health_no_snapshot` — GET /api/health returns 503 when no snapshot
- [ ] 4.4 Test: `test_snapshots_latest` — GET /api/snapshots/latest returns full snapshot JSON
- [ ] 4.5 Test: `test_skills_list` — GET /api/skills returns array sorted by load_count desc
- [ ] 4.6 Test: `test_skills_detail_found` — GET /api/skills/<name> returns 200 with per-session data
- [ ] 4.7 Test: `test_skills_detail_not_found` — GET /api/skills/nonexistent returns 404
- [ ] 4.8 Test: `test_tools_list` — GET /api/tools returns array sorted by count desc
- [ ] 4.9 Test: `test_tools_detail_not_found` — GET /api/tools/nonexistent returns 404
- [ ] 4.10 Test: `test_sessions_list` — GET /api/sessions returns array ordered by started_at desc
- [ ] 4.11 Test: `test_sessions_detail_found` — GET /api/sessions/<id> returns 200 with full session
- [ ] 4.12 Test: `test_sessions_detail_not_found` — GET /api/sessions/nonexistent returns 404
- [ ] 4.13 Test: `test_post_snapshot_valid` — POST valid JSON returns 201 and updates in-memory data
- [ ] 4.14 Test: `test_post_snapshot_invalid_json` — POST invalid JSON returns 400
- [ ] 4.15 Test: `test_post_snapshot_missing_fields` — POST JSON missing sessions returns 422
- [ ] 4.16 Test: `test_refresh_endpoint` — POST /api/refresh returns 200 with fresh snapshot

## 5. Schema Validation Tests

- [ ] 5.1 Create `tests/test_schema.py` with snapshot fixture
- [ ] 5.2 Test: `test_top_level_keys` — snapshot has generated_at, hermes_home, sessions, global_insights
- [ ] 5.3 Test: `test_generated_at_format` — generated_at matches ISO 8601 UTC pattern
- [ ] 5.4 Test: `test_session_object_structure` — each session has all required keys with correct types
- [ ] 5.5 Test: `test_empty_arrays_for_blank_sessions` — session with no skills has empty lists, not null
- [ ] 5.6 Test: `test_global_insights_structure` — correct keys and types, non-negative integers
- [ ] 5.7 Test: `test_skill_load_object_structure` — each skills_loaded entry has all required fields
- [ ] 5.8 Test: `test_tool_call_object_structure` — each tool_calls entry has tool_name, count, message_ids

## 6. Integration & Verification

- [ ] 6.1 Run full test suite with `python -m pytest tests/ -v` and verify all pass
- [ ] 6.2 Verify tests complete in under 1 second
- [ ] 6.3 Verify no test touches the real `~/.hermes/` directory
- [ ] 6.4 Add `python -m pytest tests/ -v` as the test command in README (future task, noted here)
