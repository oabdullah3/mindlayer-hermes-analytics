## ADDED Requirements

### Requirement: Health endpoint test

The API test SHALL verify that `GET /api/health` returns 200 with `status: "ok"` when a snapshot is loaded and 503 when no snapshot is available.

#### Scenario: Snapshot loaded

- **WHEN** the Flask test client calls GET /api/health after loading a snapshot
- **THEN** response is 200, body contains `{"status": "ok", "last_collection": "<timestamp>"}`

#### Scenario: No snapshot loaded

- **WHEN** the Flask test client calls GET /api/health before any snapshot is loaded
- **THEN** response is 503, body contains `{"status": "error"}`

### Requirement: Skills endpoints test

The API test SHALL verify that `GET /api/skills` returns the skills array and `GET /api/skills/:name` returns per-skill detail or 404.

#### Scenario: Skills list returned

- **WHEN** the snapshot contains skill data
- **THEN** `GET /api/skills` returns 200 with a JSON array sorted by load_count descending

#### Scenario: Specific skill found

- **WHEN** a skill name exists in the snapshot
- **THEN** `GET /api/skills/<name>` returns 200 with skill detail including sessions where it was loaded

#### Scenario: Skill not found

- **WHEN** a skill name does not exist
- **THEN** `GET /api/skills/nonexistent` returns 404 with `{"error": "Skill not found"}`

### Requirement: Tools endpoints test

The API test SHALL verify that `GET /api/tools` returns the tools array and `GET /api/tools/:name` returns per-tool detail or 404.

#### Scenario: Tools list returned

- **WHEN** tool data exists in the snapshot
- **THEN** `GET /api/tools` returns 200 with an array sorted by count descending

#### Scenario: Tool not found

- **WHEN** a tool name does not exist
- **THEN** `GET /api/tools/nonexistent` returns 404

### Requirement: Sessions endpoints test

The API test SHALL verify that `GET /api/sessions` returns all sessions and `GET /api/sessions/:id` returns single session detail or 404.

#### Scenario: Sessions list returned

- **WHEN** sessions exist in the snapshot
- **THEN** `GET /api/sessions` returns 200 with an array ordered by started_at descending

#### Scenario: Single session found

- **WHEN** a valid session ID is provided
- **THEN** `GET /api/sessions/<id>` returns 200 with the full session object including skills_loaded, tool_calls, user_messages

#### Scenario: Session not found

- **WHEN** an invalid session ID is provided
- **THEN** `GET /api/sessions/nonexistent` returns 404

### Requirement: Snapshot POST ingestion test

The API test SHALL verify that `POST /api/snapshots` accepts valid JSON and stores it, and rejects invalid payloads.

#### Scenario: Valid snapshot posted

- **WHEN** a valid snapshot JSON is POSTed with Content-Type application/json
- **THEN** response is 201, and subsequent GET /api/sessions reflects the new data

#### Scenario: Invalid JSON posted

- **WHEN** the POST body is not valid JSON
- **THEN** response is 400 with `{"error": "Invalid JSON"}`

#### Scenario: Missing required fields

- **WHEN** the POST body is valid JSON but missing `sessions` or `global_insights`
- **THEN** response is 422

### Requirement: Refresh endpoint test

The API test SHALL verify that `POST /api/refresh` triggers a collector re-run and returns fresh data.

#### Scenario: Refresh succeeds

- **WHEN** `POST /api/refresh` is called and the collector subprocess succeeds
- **THEN** response is 200 with the new snapshot data
