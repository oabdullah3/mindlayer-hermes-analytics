# Refresh Trigger

**Purpose**: Expose an endpoint that re-runs the collector as a subprocess and returns fresh snapshot data on demand — enabling on-demand data refresh without restarting the server.

## Requirements

### Requirement: Refresh endpoint triggers collector re-run

The system SHALL expose `POST /api/refresh` that executes `python collector.py` as a subprocess and returns the freshly generated snapshot.

#### Scenario: Collector succeeds

- **WHEN** `POST /api/refresh` is called and `collector.py` runs successfully
- **THEN** the server loads the newly generated `snapshot_latest.json`, returns 200 with the new snapshot, and updates the in-memory state

#### Scenario: Collector fails

- **WHEN** `POST /api/refresh` is called and `collector.py` exits with non-zero status
- **THEN** the server returns 500 with `{"error": "Collector failed", "details": "<stderr output>"}` and does not update the in-memory snapshot

#### Scenario: Collector times out

- **WHEN** `POST /api/refresh` is called and `collector.py` runs longer than 60 seconds
- **THEN** the server kills the subprocess and returns 504 with `{"error": "Collector timed out after 60s"}`

### Requirement: Refresh preserves existing snapshot on failure

If the collector re-run fails, the system SHALL continue serving the previously loaded snapshot rather than clearing in-memory data.

#### Scenario: Refresh fails after prior successful load

- **WHEN** a snapshot was previously loaded and a refresh fails
- **THEN** subsequent GET requests continue to return the old snapshot, and `GET /api/health` still reports `status: "ok"`