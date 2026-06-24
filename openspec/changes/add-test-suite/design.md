## Context

The collector reads from an external SQLite database (`~/.hermes/state.db`) whose contents are an unknown quantity — we don't control what sessions, messages, skills, or tools are present. We need synthetic test fixtures that exercise every code path so we can verify correctness deterministically. The fixture must simulate a realistic Hermes state.db with all data shapes the collector might encounter.

Current state: No tests exist. The collector, server, and schema specs are defined but unverified.

Constraints:
- The test fixture must be a valid SQLite database in the exact schema Hermes writes
- Tests must not depend on a real `~/.hermes/` directory existing
- Tests must be fast (< 1s total suite) — no real file I/O beyond the fixture DB
- Must use pytest as the test runner (Python ecosystem standard)

## Goals / Non-Goals

**Goals:**
- A synthetic state.db that exercises: multiple sessions, multiple platforms, skill loads, tool calls, user messages, assistant messages with tool_calls JSON, token counts, varied message counts
- Collector tests that verify: session count, skill detection accuracy, preceding user message resolution, tool aggregation, token estimation math, error parsing, global insights computation
- API tests that verify: all 10 endpoints, correct status codes, correct JSON shapes, 404 on missing resources, 503 on missing snapshot
- Schema tests that validate: snapshot top-level keys, session object structure, global_insights structure, type correctness
- All tests runnable with a single command: `python -m pytest tests/ -v`

**Non-Goals:**
- Testing with a real Hermes installation (that's integration testing, not unit testing)
- Performance/load testing
- Testing Grafana dashboard rendering (visual tests — out of scope)
- Mocking the entire Hermes ecosystem — we test against real SQLite, real collector code
- 100% code coverage — focus on critical paths and edge cases

## Decisions

### Decision 1: pytest over unittest

**Chosen:** pytest with fixtures, parametrize, and tmp_path.
**Alternatives considered:** Python's built-in `unittest` — less ergonomic, more boilerplate.
**Rationale:** pytest is the Python ecosystem standard. Fixtures make it easy to share the synthetic DB across tests. `tmp_path` gives isolated temp directories.

### Decision 2: Synthetic state.db built in conftest.py, not a checked-in binary

**Chosen:** Build the test database programmatically in `conftest.py` using `sqlite3` within a pytest fixture. Not a pre-built `.db` file.
**Alternatives considered:** Check in a binary `state.db` file — not diffable, opaque, hard to update.
**Rationale:** Python code that creates the DB is self-documenting. Anyone can read `conftest.py` and see exactly what test data exists. Easy to extend.

### Decision 3: Test against the real collector module, not mocked SQLite

**Chosen:** Import `collector` as a module and call its functions with the fixture DB path. Use `HERMES_HOME` env var to point at the fixture.
**Rationale:** We want to catch real bugs in the collector, not test mocks. The synthetic DB provides controlled input; the collector is the system under test.

### Decision 4: API tests use Flask test client, not live server

**Chosen:** Use `app.test_client()` from Flask's test utilities.
**Rationale:** No port binding, no subprocess, no race conditions. Tests run in-process and are fast.

### Decision 5: Fixture data covers 3 sessions with distinct characteristics

**Chosen:**
- Session 1 (telegram): 2 skill loads, 5 tool calls, has errors, has token counts
- Session 2 (discord): 0 skill loads, 8 tool calls, no errors
- Session 3 (cli): 1 skill load, 3 tool calls, has errors
**Rationale:** This exercises the "all features present" check — skill detection, empty-skill sessions, multi-platform, error presence/absence, varied tool counts.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Fixture DB schema drifts from real Hermes schema | Base fixture on the documented schema in PLAN.md. Update if Hermes schema changes. |
| Collector is designed as a script, not an importable module | Ensure collector has a `main()` or equivalent callable entry point. Refactor if needed. |
| Flask test client behaves differently than real HTTP | Test client is well-proven. Add one smoke test against a live server if needed later. |
| Tests pass with fixture but fail with real data | This is expected — fixture tests cover code paths, not data diversity. Real-world testing is a separate concern. |

## Open Questions

1. Should the fixture also include `sessions/*.jsonl` files for fuller integration testing? (Adds complexity — start with state.db only.)
2. Should we add `tox` or `nox` for multi-Python-version testing? (Premature for v1.)
3. Should tests be run in CI? (Yes, but CI setup is out of scope for this change.)
