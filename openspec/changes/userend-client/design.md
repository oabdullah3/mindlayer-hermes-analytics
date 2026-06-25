## Context

The collector (`collector.py`, ~1000 lines) currently lives at the repo root. It's a standalone script with no install mechanism, no agent integration, and no user identity — you run `python collector.py` from a terminal. ADRs 0001 and 0003 (now accepted) define a different model: an agent-invocable skill installed per-user, configured with a username at install time, producing snapshot JSON as the universal data contract.

This design covers the structural reorganization to make the collector a proper user-side client, the backward-compatibility strategy, agent slash command integration per ADR-0001, and the explicit decision to remain on Python.

## Goals / Non-Goals

**Goals:**
- Move collector into `userend/` as a self-contained, installable client
- Guarantee snapshot output is identical to current collector (backward compatible)
- Implement ADR-0001: slash commands, inline summary, `~/.hermes-analytics.conf`
- Document the Python-sufficiency decision with rationale
- Keep root `collector.py` working during transition (deprecation wrapper)

**Non-Goals:**
- Changing the extraction pipeline or snapshot schema (ADR-0003 remains as-is)
- Adding new dependencies or changing requirements.txt (flat-file persistence uses only stdlib)
- Authentication/authorization on the server — all data visible to all users per ADR-0002
- Data retention/cleanup policies — snapshots accumulate indefinitely

## Decisions

### Decision 1: Python stays — no Node.js migration

**Chosen:** Keep the collector as Python 3. No migration to Node.js.

**Rationale:** The collector's dependency footprint is pure Python stdlib: `sqlite3` (read-only state.db queries), `json`, `os`, `re`, `math`, `argparse`, `sys`, `datetime`. The only optional dependency is `requests` for remote push mode. A Node.js port would require `better-sqlite3` (native C++ compilation, platform-specific binaries) for equivalent SQLite access, adding build complexity with zero benefit. The snapshot generation runs in under 2 seconds for 116 sessions — performance is a non-issue. The agent skill invocation pattern (`/hermes-snapshot` → runs a script) is language-agnostic; Python is already installed on every system that runs Hermes (Hermes itself is Python-based).

**Alternatives considered:** Node.js with better-sqlite3 (rejected — native module compilation pain), TypeScript/Deno with deno-sqlite (rejected — requires Deno runtime, not universally available).

### Decision 2: Root collector.py is a deprecation wrapper, not a symlink

**Chosen:** Keep a thin `collector.py` at the repo root that imports and delegates to `userend/collector.py`, with a deprecation notice to stderr.

**Rationale:** Symlinks break on some filesystems and confuse Windows users. A wrapper script preserves the existing `python collector.py` workflow while guiding users to the new path. `server.py`'s `/api/refresh` endpoint can be updated to call `userend/collector.py` directly.

**Wrapper behavior:**
```python
#!/usr/bin/env python3
"""Deprecated: use userend/collector.py instead."""
import sys, os
sys.stderr.write("[DEPRECATED] collector.py moved to userend/collector.py\n")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "userend"))
from collector import main
main()
```

### Decision 3: Snapshot compatibility via JSON deep-compare test

**Chosen:** A dedicated test script `userend/test_snapshot_compat.py` that runs both collectors, normalizes `generated_at` timestamps, and deep-compares the JSON trees.

**Rationale:** The move must not alter any extraction logic. The test catches regressions from import path changes, working directory assumptions, or relative path resolution. The `generated_at` field is exempted from comparison (it will always differ between runs). All other fields — session data, global_insights, arrays, nested objects — must match exactly.

### Decision 4: Agent slash commands via skill manifest + shell wrapper

**Chosen:** A shell script `userend/hermes-snapshot` that wraps `python3 userend/collector.py`, reads config, and outputs an inline summary. The agent registers it as a skill with two slash commands.

**Rationale:** ADR-0001 specifies the agent invokes a command — the simplest interface is a shell script that the agent's skill system can call. The script:
1. Sources `~/.hermes-analytics.conf` for HERMES_ANALYTICS_USER and HERMES_ANALYTICS_REMOTE
2. Runs the collector
3. Parses the output to emit an inline summary (session count, skill count, tool count, errors)
4. For `/hermes-snapshot dashboard`, additionally prints the dashboard URL

**Non-goal:** We are NOT building a full agent skill manifest in this change. The agent platform's skill registration mechanism is Hermes-specific and belongs in a separate integration spec. This change creates the script that any agent platform can invoke.

### Decision 5: Config file as shell-sourceable key=value

**Chosen:** `~/.hermes-analytics.conf` uses simple `KEY=value` lines, one per line.

**Rationale:** Sourceable by both bash scripts (`source ~/.hermes-analytics.conf`) and Python (`os.environ` after reading). No JSON, YAML, or INI parsing needed. The install script writes it; the collector reads it.

Format:
```
HERMES_ANALYTICS_USER=alice
HERMES_ANALYTICS_REMOTE=https://hermes-dash.example.com
```

### Decision 6: Directory structure

**Chosen:**
```
userend/
├── collector.py              # The collector, moved from root (identical logic)
├── install.sh                # User-side setup: prompt for username, write config
├── hermes-snapshot           # Shell wrapper for agent slash command invocation
├── test_snapshot_compat.py   # Automated snapshot diff test
└── __init__.py               # Makes userend a Python package
```

**Rationale:** Self-contained under one directory. Everything a user needs is in `userend/`. The root `install.sh` (build-installer change) can call `userend/install.sh` as a sub-step for the user-side config.

### Decision 7: Multi-user server per ADR-0002 — flat-file persistence

**Chosen:** Evolve `server.py` to persist snapshots as flat JSON files at `server_data/{username}/snapshot_YYYY-MM-DD_HHMMSS.json`. Remove in-memory `_SNAPSHOT` variable. Add user-scoped and leaderboard endpoints.

**Rationale:** ADR-0002 is accepted — the current in-memory single-snapshot design is non-compliant. Flat files require zero new dependencies, are debuggable with `cat`, and scale to <100 users. The existing single-user local mode (Mode A) is preserved as fallback when `server_data/` is empty — `load_snapshot()` reads `snapshot_latest.json` the old way.

**Server behavior:**
1. `POST /api/snapshots` validates `username`, `sessions`, `global_insights`
2. Creates `server_data/{username}/` directory
3. Writes timestamped snapshot JSON
4. Returns 201

**New endpoints:** `GET /api/users`, `GET /api/users/<username>/latest`, `GET /api/users/<username>/history`, `GET /api/users/<username>/<timestamp>`, `GET /api/leaderboard/sessions`, `GET /api/leaderboard/skills`, `GET /api/leaderboard/tools`

**Modified endpoints:** Existing `/api/skills`, `/api/tools`, `/api/sessions`, `/api/sessions/:id` accept `?username=` query parameter. Without it, they aggregate across all users.

**Alternatives considered:** SQLite (rejected — adds schema migration burden, flat files simpler for this scale).

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Moving collector.py breaks relative imports or file path assumptions | Snapshot compat test catches this; the wrapper at root preserves old behavior |
| `generated_at` changes make naive diff tools report false failures | Compat test normalizes timestamps before comparison |
| Users with scripts pointing to `./collector.py` break | Root deprecation wrapper ensures `python collector.py` still works for at least one release cycle |
| `requests` import for remote push fails if userend/ changes sys.path | The wrapper adds userend/ to sys.path before import; compat test verifies remote push path |
| Agent platform's skill registration format is unknown | We create the invocable script; actual skill manifest is deferred to agent-specific integration |

## Migration Plan

1. Create `userend/` directory with collector.py (copy, don't move yet)
2. Write `test_snapshot_compat.py` and verify identical output
3. Replace root `collector.py` with deprecation wrapper
4. Update `server.py` `/api/refresh` to call `userend/collector.py`
5. Create `userend/install.sh` and `userend/hermes-snapshot`
6. After one release cycle with no issues, remove the root wrapper

**Rollback:** Restore root `collector.py` from git history. The snapshot schema is unchanged, so rollback has zero data impact.

## Open Questions

- What is the exact agent skill manifest format for Hermes Agent? (Deferred to agent-platform-specific integration)
- Should `userend/install.sh` be a standalone script or called from the root `install.sh`? (Recommend: standalone, invoked by root install.sh as a sub-step)
- Should `HERMES_ANALYTICS_USER` default to `$USER` if not configured? (ADR-0001 says no — explicit prompt at install time — but a fallback may improve UX for unattended installs)
