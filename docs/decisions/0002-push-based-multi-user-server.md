---
status: "accepted"
date: 2026-06-24
decision-makers: "oabdullah3"
---

# Push-based multi-user server with flat-file persistence

## Context and Problem Statement

The current server (`server.py`) holds a single snapshot in memory — each `POST /api/snapshots` overwrites the previous. This works for a single user but cannot support the multi-user, historical scenario where:

- Multiple users push snapshots to a shared server
- Each user's history is retained (not overwritten by the next push)
- The server dashboard shows cross-user analytics (leaderboards, time series)
- Individual user detailed sessions are drillable

The server has no way of knowing who wants to send it a snapshot; all clients who know the server URL push to it. This push model (clients → server) is already established via `HERMES_ANALYTICS_REMOTE` and `POST /api/snapshots`. The question is how to evolve that endpoint for multi-user persistence.

Constraints:
- No new heavy dependencies (Python stdlib preferred)
- Must remain simple to deploy (single Flask process, no Docker requirement)
- Existing single-user local mode must continue working unmodified
- Username established at install time (see ADR-0001)

## Decision

**Evolve the server to persist snapshots as flat JSON files keyed by username and timestamp. Each snapshot POSTed by a client includes a username, and the server stores it at `server_data/{username}/snapshot_YYYY-MM-DD_HHMMSS.json`.**

### Data layout

```
server_data/
├── alice/
│   ├── snapshot_2026-06-24_091523.json
│   └── snapshot_2026-06-24_145302.json
├── bob/
│   └── snapshot_2026-06-23_180045.json
└── carol/
    ├── snapshot_2026-06-24_080000.json
    └── snapshot_2026-06-24_120000.json
```

### Username in the push

The collector already reads `HERMES_ANALYTICS_USER` from `~/.hermes-analytics.conf` (see ADR-0001). It includes the username in the POST JSON body alongside `sessions` and `global_insights`:

```json
{
  "username": "alice",
  "generated_at": "2026-06-24T09:15:23+00:00",
  "hermes_home": "/home/alice/.hermes",
  "sessions": [...],
  "global_insights": {...}
}
```

### Server behavior on `POST /api/snapshots`

1. Validate required fields: `username`, `sessions`, `global_insights`
2. Create `server_data/{username}/` directory if it doesn't exist
3. Write the full snapshot JSON to `server_data/{username}/snapshot_{timestamp}.json`
4. Return 201 with `{"status": "accepted", "sessions": <count>}`

The in-memory `_SNAPSHOT` variable is removed — it was single-user only. The server reads from disk on demand for serving endpoints.

### New API endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/users` | List of all usernames with snapshot counts |
| `GET /api/users/<username>/latest` | Most recent snapshot for a user |
| `GET /api/users/<username>/history` | List of all snapshots for a user with timestamps |
| `GET /api/users/<username>/<timestamp>` | Specific historical snapshot |
| `GET /api/leaderboard/sessions` | All users ranked by total sessions |
| `GET /api/leaderboard/skills` | All users ranked by skill loads |
| `GET /api/leaderboard/tools` | All users ranked by tool calls |

Existing endpoints (`/api/skills`, `/api/sessions`, etc.) are updated to accept `?username=` query parameter. Without it, they aggregate across all users for the team dashboard.

### Backward compatibility

The single-user local mode (Mode A) is unchanged — `collector.py` still writes `snapshot_latest.json` locally when `HERMES_ANALYTICS_REMOTE` is unset. The local `server.py` can still serve that file via existing endpoints (fallback mode when `server_data/` is empty).

### Non-goals

- Authentication/authorization — all data is visible to all users (per the decision-maker)
- Data retention/cleanup policies — snapshots accumulate indefinitely (simple for now)
- Real-time WebSocket updates — the dashboard polls or refreshes on page load

## Consequences

- Good, because flat files require zero new dependencies and are debuggable with `cat`
- Good, because `server_data/` can be backed up with `rsync` or `tar`
- Good, because each user's data is isolated in their own directory
- Good, because timestamps in filenames make history queries trivial (glob + sort)
- Bad, because flat files don't scale to thousands of users (acceptable — this is a team tool, not SaaS)
- Bad, because no built-in deduplication (same snapshot pushed twice = two files)
- Bad, because cross-user aggregation requires reading all files into memory (acceptable for current scale of <100 users)

## Implementation Plan

- **Affected paths**: `server.py` (major changes to persistence and endpoints), `collector.py` (add `HERMES_ANALYTICS_USER` to POST body), new: `server_data/` directory (gitignored)
- **Dependencies**: None new — `os`, `json`, `glob`, `datetime` are stdlib
- **Patterns to follow**: `_require_snapshot()` pattern evolves to `_load_user_snapshot(username, timestamp)`; `_json()` response helper unchanged
- **Patterns to avoid**: Introducing a database ORM; complex query DSL; breaking existing single-user API contract

### Verification

- [ ] `POST /api/snapshots` with `username: "alice"` creates `server_data/alice/snapshot_*.json`
- [ ] `GET /api/users` returns `["alice"]` with snapshot count 1
- [ ] `GET /api/users/alice/latest` returns the snapshot
- [ ] `GET /api/users/alice/history` returns a list with one entry
- [ ] `GET /api/leaderboard/sessions` ranks all users by session count
- [ ] `GET /api/sessions?username=alice` returns only alice's sessions
- [ ] `GET /api/sessions` (no username) aggregates across all users
- [ ] Existing single-user mode works unmodified when `HERMES_ANALYTICS_REMOTE` is unset
- [ ] Pushing the same snapshot twice creates two files (no dedup)
- [ ] `server_data/` is listed in `.gitignore`

## Alternatives Considered

- **SQLite database**: Rejected — adds schema migration burden, still single-file, overkill for <100 users. Flat files are simpler to inspect and back up.
- **In-memory only (current)**: Rejected — cannot support multi-user or history. Already documented as a limitation.
- **Directory-per-snapshot with sessions split into sub-files**: Rejected — the snapshot is self-contained by design; splitting it loses the "one artifact" property.

## More Information

- Username is established at install time via [ADR-0001](./0001-agent-native-skill-distribution.md)
- The snapshot schema POSTed to this server follows [ADR-0003](./0003-snapshot-as-universal-data-contract.md)
- `server_data/` directory must be added to `.gitignore`
