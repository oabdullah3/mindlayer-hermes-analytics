## Why

Without tests, regressions in the data collection pipeline or REST API go undetected. The collector reads from an external database (state.db) whose contents we don't control — we need synthetic fixtures that exercise every extraction path (skills, tools, errors, token estimates, multi-session, multi-message) so we can verify the collector correctly handles all data shapes. This must be in place before the other components are built, so each can be validated as it's implemented.

## What Changes

- New `tests/` directory with pytest-based test suite
- New `tests/fixtures/` directory with a synthetic `state.db` pre-populated with known data:
  - 3 sessions across different platforms (telegram, discord, cli)
  - Multiple messages per session (user, assistant, tool roles)
  - Skill loads via `skill_view` tool calls with linked tool responses
  - Tool calls (`terminal`, `browser_navigate`, `skill_view`, `read_file`)
  - Token counts on session rows
  - Varied message counts and tool_call_counts per session
- New `tests/conftest.py` with shared fixtures (db path, collector invocation, snapshot loader)
- Collector tests: verify all 7 extraction steps, snapshot schema, global insights accuracy
- API tests: verify all 10 REST endpoints return correct status codes and response shapes
- Schema validation tests: ensure snapshot JSON matches the documented schema contract
- `requirements.txt` extended with `pytest`
- All tests runnable via `python -m pytest tests/ -v`

## Capabilities

### New Capabilities

- `test-fixtures`: Synthetic Hermes state.db and supporting files that exercise every collector code path — multi-session, multi-platform, skill loads, tool calls, token counts, and errors
- `collector-tests`: Pytest suite verifying the collector correctly extracts sessions, skill loads, preceding user messages, tool calls, token estimates, user messages, errors, and global insights from the fixture database
- `api-tests`: Pytest suite verifying REST API endpoints return correct JSON, proper status codes (200, 404, 503), and handle edge cases (missing snapshot, invalid POST, refresh failure)
- `schema-tests`: Pytest suite validating that generated snapshots conform to the documented JSON schema (required keys, types, non-null fields)

### Modified Capabilities

None — this adds net-new testing infrastructure.

## Impact

- **New directory:** `tests/` with `__init__.py`, `conftest.py`
- **New directory:** `tests/fixtures/` with synthetic `state.db`
- **New files:** `tests/test_collector.py`, `tests/test_api.py`, `tests/test_schema.py`
- **Modified:** `requirements.txt` — add `pytest`
- **No production code changes** — purely additive testing layer
- **Dependencies:** `pytest`, Python stdlib (`sqlite3`, `tempfile`, `json`, `unittest.mock`)
