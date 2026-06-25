## MODIFIED Requirements

### Requirement: Collector supports remote push mode

When the `HERMES_ANALYTICS_REMOTE` environment variable is set, the system SHALL POST the generated snapshot JSON to `{HERMES_ANALYTICS_REMOTE}/api/snapshots` in addition to pushing to the local server and writing a local file. The remote push is NOT an exclusive alternative to local output.

#### Scenario: Remote push enabled and successful

- **WHEN** `HERMES_ANALYTICS_REMOTE` is set to `https://hermes-dash.example.com` and the remote server accepts the POST
- **THEN** the collector sends the snapshot via HTTP POST with Content-Type application/json and prints a success message
- **AND** the collector also pushes to the local server and writes `snapshot_latest.json` locally

#### Scenario: Remote push fails

- **WHEN** `HERMES_ANALYTICS_REMOTE` is set but the remote server is unreachable or returns a non-2xx status
- **THEN** the collector logs the error and continues — local server push and local file save are unaffected

## ADDED Requirements

### Requirement: Collector pushes to local server first

The collector SHALL attempt to POST the snapshot to the local server at `http://localhost:{port}/api/snapshots` before attempting the remote push.

#### Scenario: Local server is running

- **WHEN** the local server (started by the slash command) is listening on port 5555
- **THEN** the collector POSTs the snapshot to `http://localhost:5555/api/snapshots`
- **AND** on success, prints: "Pushed to local server"

#### Scenario: Local server is not running

- **WHEN** no local server is running (collector run standalone, not via slash command)
- **THEN** the collector skips the local server push and attempts remote push (if configured)

### Requirement: Push priority is local → remote → file

The collector SHALL follow the push order: local server, then remote server, then local file. Each step is attempted regardless of previous step failures.

#### Scenario: All destinations succeed

- **WHEN** local server, remote server, and local file are all available
- **THEN** the snapshot is pushed to all three destinations
- **AND** the collector reports: "Pushed to local server, remote server, and saved locally"

#### Scenario: Only local file succeeds

- **WHEN** both local and remote servers are unreachable
- **THEN** the collector writes `snapshot_latest.json` locally
- **AND** reports: "Saved locally (local server and remote server unavailable)"

### Requirement: Local file is always written

Regardless of push success to any server, the collector SHALL always write `snapshot_latest.json` to the current working directory as a backup.

#### Scenario: All pushes succeed

- **WHEN** the snapshot is successfully pushed to local and remote servers
- **THEN** `snapshot_latest.json` is still written locally
