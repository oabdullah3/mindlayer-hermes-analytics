## ADDED Requirements

### Requirement: Collector outputs a valid snapshot JSON file

The system SHALL write the assembled data to `snapshot_latest.json` in the current working directory with a schema matching: `generated_at` (ISO 8601 timestamp), `hermes_home` (path string), `sessions` (array of session objects), `global_insights` (aggregate statistics object).

#### Scenario: Successful snapshot generation

- **WHEN** collector completes all extraction steps without fatal errors
- **THEN** `snapshot_latest.json` is written to disk with valid JSON and non-null `generated_at`

#### Scenario: File write permission denied

- **WHEN** the current directory is not writable
- **THEN** the collector exits with a non-zero status and prints an error to stderr

### Requirement: Snapshot session object conforms to schema

Each session object in the snapshot SHALL include fields: session_id, source, model, started_at, ended_at, ended_reason, platform, chat_name, tokens (input, output, cache_read, cache_write, reasoning, estimated_cost_usd), stats (message_count, tool_call_count), skills_loaded (array), tool_calls (array), user_messages (array), errors (array).

#### Scenario: Session with all data populated

- **WHEN** a session has skills, tools, user messages, and errors
- **THEN** all fields in the session object are populated with non-empty arrays where applicable

#### Scenario: Session with no skills or errors

- **WHEN** a session has no skill loads, no tool calls, and no errors
- **THEN** the session object has empty arrays for skills_loaded, tool_calls, user_messages, and errors

### Requirement: Snapshot global_insights object conforms to schema

The `global_insights` object SHALL include: total_sessions (integer), total_messages (integer), total_skill_loads (integer), skills (array of {name, load_count, total_chars, token_estimate}), tools (array of {name, count}).

#### Scenario: Global insights computed correctly

- **WHEN** the snapshot has 10 sessions, 500 messages, 25 skill loads, 150 tool calls
- **THEN** `global_insights` reflects these totals accurately

### Requirement: generated_at timestamp is ISO 8601 UTC

The `generated_at` field SHALL be an ISO 8601 formatted UTC timestamp at the moment snapshot generation completes.

#### Scenario: Timestamp format

- **WHEN** collector finishes generating the snapshot
- **THEN** `generated_at` matches the pattern `YYYY-MM-DDTHH:MM:SS+00:00` or `YYYY-MM-DDTHH:MM:SSZ`
