# Remote Ingestion

**Purpose**: Accept snapshot POSTs from remote collector instances, enabling multi-user and team dashboard scenarios (Mode B) where collectors push data to a shared server. Snapshots are persisted per-user as timestamped JSON files in `server_data/`.

## Requirements

### Requirement: Server accepts snapshot POST from remote collectors

The system SHALL expose `POST /api/snapshots` accepting a JSON body matching the snapshot schema with a required `username` field, and persisting each snapshot as a flat JSON file at `server_data/{username}/snapshot_YYYY-MM-DD_HHMMSS.json`. The in-memory `_SNAPSHOT` variable is removed — the server reads from disk on demand.

#### Scenario: Valid snapshot posted with username

- **WHEN** a collector POSTs a valid snapshot JSON with `"username": "alice"` to `/api/snapshots` with Content-Type `application/json`
- **THEN** the server creates `server_data/alice/` directory if it doesn't exist, writes the full snapshot to `server_data/alice/snapshot_{current_utc_timestamp}.json`, and returns 201 with `{"status": "accepted", "sessions": <count>}`

#### Scenario: Missing username field

- **WHEN** the POST body is valid JSON but missing `username`
- **THEN** the server returns 422 with `{"error": "Missing required field: username"}`

#### Scenario: Invalid JSON posted

- **WHEN** the POST body is not valid JSON
- **THEN** the server returns 400 with `{"error": "Invalid JSON"}`

#### Scenario: Missing required fields

- **WHEN** the POST body is valid JSON but missing `sessions` or `global_insights`
- **THEN** the server returns 422 with `{"error": "Missing required fields: sessions, global_insights"}`

#### Scenario: Same snapshot pushed twice

- **WHEN** the same snapshot is POSTed twice with the same username
- **THEN** two separate timestamped files are created (no deduplication)

### Requirement: Remote push does not overwrite local file

The system SHALL persist snapshots received via POST to `server_data/{username}/` and SHALL NOT modify `snapshot_latest.json` on disk. The local `snapshot_latest.json` is only written by the collector in local mode (when `HERMES_ANALYTICS_REMOTE` is unset).

#### Scenario: Remote POST received while snapshot_latest.json exists

- **WHEN** a snapshot is POSTed to `/api/snapshots` and `snapshot_latest.json` exists on disk
- **THEN** `snapshot_latest.json` is not modified; the snapshot is written only to `server_data/{username}/snapshot_{timestamp}.json`

### Requirement: Server serves per-user snapshots

The server SHALL expose user-scoped endpoints that return snapshots by username, with the most recent snapshot available at `/api/users/<username>/latest`.

#### Scenario: Get latest snapshot for a user

- **WHEN** `GET /api/users/alice/latest` is called
- **AND** `server_data/alice/` contains at least one snapshot
- **THEN** the most recent snapshot by timestamp is returned

#### Scenario: User has no snapshots

- **WHEN** `GET /api/users/bob/latest` is called
- **AND** `server_data/bob/` does not exist or is empty
- **THEN** the server returns 404 with `{"error": "No snapshots found for user: bob"}`

### Requirement: Server lists all users

The system SHALL expose `GET /api/users` returning a list of all usernames with their snapshot counts.

#### Scenario: Multiple users have pushed snapshots

- **WHEN** `GET /api/users` is called
- **AND** `server_data/` contains directories `alice/` (2 snapshots) and `bob/` (1 snapshot)
- **THEN** the response is `[{"username": "alice", "snapshot_count": 2}, {"username": "bob", "snapshot_count": 1}]`

#### Scenario: No users have pushed yet

- **WHEN** `GET /api/users` is called and `server_data/` is empty
- **THEN** the response is `[]`

### Requirement: Server provides snapshot history per user

The system SHALL expose `GET /api/users/<username>/history` returning a list of all snapshot timestamps for a user, ordered newest first.

#### Scenario: User has multiple snapshots

- **WHEN** `GET /api/users/alice/history` is called
- **AND** `server_data/alice/` contains `snapshot_2026-06-24_091523.json` and `snapshot_2026-06-24_145302.json`
- **THEN** the response lists both timestamps: `["2026-06-24_145302", "2026-06-24_091523"]`

### Requirement: Server serves historical snapshots by timestamp

The system SHALL expose `GET /api/users/<username>/<timestamp>` to retrieve a specific historical snapshot.

#### Scenario: Specific timestamp exists

- **WHEN** `GET /api/users/alice/2026-06-24_091523` is called
- **AND** `server_data/alice/snapshot_2026-06-24_091523.json` exists
- **THEN** the full snapshot JSON is returned

#### Scenario: Timestamp not found

- **WHEN** `GET /api/users/alice/2026-06-24_000000` is called
- **AND** no snapshot matches that timestamp
- **THEN** the server returns 404

### Requirement: Leaderboard endpoints

The system SHALL expose leaderboard endpoints ranking all users by session count, skill loads, and tool calls.

#### Scenario: Sessions leaderboard

- **WHEN** `GET /api/leaderboard/sessions` is called
- **THEN** users are returned ranked by total session count descending, each with `username` and `total_sessions`

#### Scenario: Skills leaderboard

- **WHEN** `GET /api/leaderboard/skills` is called
- **THEN** users are returned ranked by total skill loads descending, each with `username` and `total_skill_loads`

#### Scenario: Tools leaderboard

- **WHEN** `GET /api/leaderboard/tools` is called
- **THEN** users are returned ranked by total tool calls descending, each with `username` and `total_tool_calls`

### Requirement: Existing endpoints support username filtering

The existing endpoints `/api/skills`, `/api/tools`, `/api/sessions`, and `/api/sessions/:id` SHALL accept an optional `?username=` query parameter to scope results to a single user.

#### Scenario: Skills filtered by username

- **WHEN** `GET /api/skills?username=alice` is called
- **THEN** only skills loaded in alice's most recent snapshot are returned

#### Scenario: Sessions without username aggregates all users

- **WHEN** `GET /api/sessions` is called with no `username` parameter
- **THEN** sessions from all users' most recent snapshots are aggregated and returned

### Requirement: Single-user local mode preserved

The server SHALL fall back to reading `snapshot_latest.json` from disk (the current behavior) when `server_data/` is empty or does not exist, preserving backward compatibility with Mode A (local single-user).

#### Scenario: Local mode when no remote snapshots exist

- **WHEN** `server_data/` is empty and `snapshot_latest.json` exists on disk
- **THEN** `GET /api/sessions` returns sessions from `snapshot_latest.json`
- **AND** `GET /api/users` returns `[]`