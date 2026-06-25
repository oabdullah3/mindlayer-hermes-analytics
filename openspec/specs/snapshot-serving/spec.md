# Snapshot Serving

**Purpose**: Serve the latest snapshot and its sub-resources (skills, tools, sessions) as structured JSON via REST endpoints — providing the contract between the data collector backend and the Streamlit dashboard frontend.

## Requirements

### Requirement: Health endpoint returns server status

The system SHALL expose `GET /api/health` returning a JSON object with `status: "ok"` and the `generated_at` timestamp from the loaded snapshot, or `status: "error"` if no snapshot is loaded.

#### Scenario: Snapshot loaded

- **WHEN** the server has loaded a valid `snapshot_latest.json` at startup
- **THEN** `GET /api/health` returns 200 with `{"status": "ok", "last_collection": "<ISO 8601 timestamp>"}`

#### Scenario: No snapshot available

- **WHEN** no `snapshot_latest.json` exists at startup
- **THEN** `GET /api/health` returns 503 with `{"status": "error", "message": "No snapshot available. Run collector.py first."}`

### Requirement: Latest snapshot endpoint returns full snapshot

The system SHALL expose `GET /api/snapshots/latest` returning the complete snapshot JSON as loaded from `snapshot_latest.json`.

#### Scenario: Snapshot available

- **WHEN** `snapshot_latest.json` is loaded
- **THEN** `GET /api/snapshots/latest` returns 200 with the full snapshot dict including `generated_at`, `hermes_home`, `sessions`, and `global_insights`

#### Scenario: Snapshot not available

- **WHEN** no snapshot has been loaded
- **THEN** `GET /api/snapshots/latest` returns 503 with an error message

### Requirement: Skills list endpoint returns aggregated skills

The system SHALL expose `GET /api/skills` returning the `global_insights.skills` array from the snapshot — a flat list of all skills with load_count, total_chars, and token_estimate across all sessions.

#### Scenario: Skills exist in snapshot

- **WHEN** the snapshot contains skill data in `global_insights.skills`
- **THEN** `GET /api/skills` returns 200 with an array of skill objects sorted by load_count descending

#### Scenario: No skills in snapshot

- **WHEN** `global_insights.skills` is empty
- **THEN** `GET /api/skills` returns 200 with an empty array

### Requirement: Single skill detail endpoint

The system SHALL expose `GET /api/skills/:name` returning per-session detail for a specific skill, including which sessions loaded it, when, and with what preceding user messages.

#### Scenario: Skill found

- **WHEN** the skill `confluence-skill` exists in at least one session
- **THEN** `GET /api/skills/confluence-skill` returns 200 with skill name, total load count, and a list of sessions where it was loaded with timestamps and preceding_user_messages

#### Scenario: Skill not found

- **WHEN** the skill `nonexistent-skill` is not in any session
- **THEN** `GET /api/skills/nonexistent-skill` returns 404 with `{"error": "Skill not found"}`

### Requirement: Tools list endpoint returns aggregated tools

The system SHALL expose `GET /api/tools` returning the `global_insights.tools` array — a flat list of all tools with call counts across all sessions.

#### Scenario: Tools exist

- **WHEN** tools have been called across sessions
- **THEN** `GET /api/tools` returns 200 with an array of tool objects sorted by count descending

### Requirement: Single tool detail endpoint

The system SHALL expose `GET /api/tools/:name` returning per-session detail for a specific tool.

#### Scenario: Tool found

- **WHEN** the tool `terminal` exists in at least one session
- **THEN** `GET /api/tools/terminal` returns 200 with tool name, total call count, and list of sessions with call counts

### Requirement: Sessions list endpoint

The system SHALL expose `GET /api/sessions` returning the `sessions` array from the snapshot with all session metadata.

#### Scenario: Sessions exist

- **WHEN** the snapshot contains sessions
- **THEN** `GET /api/sessions` returns 200 with an array of session objects ordered by started_at descending

### Requirement: Single session detail endpoint

The system SHALL expose `GET /api/sessions/:id` returning the full session object including skills_loaded, tool_calls, user_messages, and errors.

#### Scenario: Session found

- **WHEN** session ID `20260623_105254_d434493c` exists
- **THEN** `GET /api/sessions/20260623_105254_d434493c` returns 200 with the complete session object

#### Scenario: Session not found

- **WHEN** session ID does not exist
- **THEN** `GET /api/sessions/nonexistent` returns 404 with error message