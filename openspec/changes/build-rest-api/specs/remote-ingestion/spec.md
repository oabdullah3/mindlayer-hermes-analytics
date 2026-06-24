## ADDED Requirements

### Requirement: Server accepts snapshot POST from remote collectors

The system SHALL expose `POST /api/snapshots` accepting a JSON body matching the snapshot schema and storing it as the current snapshot in memory.

#### Scenario: Valid snapshot posted

- **WHEN** a collector POSTs a valid snapshot JSON to `/api/snapshots` with Content-Type `application/json`
- **THEN** the server stores the snapshot in memory, returns 201 with `{"status": "accepted", "sessions": <count>}`, and subsequent GET requests reflect the new data

#### Scenario: Invalid JSON posted

- **WHEN** the POST body is not valid JSON
- **THEN** the server returns 400 with `{"error": "Invalid JSON"}`

#### Scenario: Missing required fields

- **WHEN** the POST body is valid JSON but missing `sessions` or `global_insights`
- **THEN** the server returns 422 with `{"error": "Missing required fields: sessions, global_insights"}`

### Requirement: Remote push does not overwrite local file

The system SHALL store snapshots received via POST only in memory and SHALL NOT write to `snapshot_latest.json` on disk unless explicitly configured.

#### Scenario: Remote POST received

- **WHEN** a snapshot is POSTed to `/api/snapshots`
- **THEN** `snapshot_latest.json` on disk is not modified; only the in-memory representation is updated
