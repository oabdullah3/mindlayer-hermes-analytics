## ADDED Requirements

### Requirement: Collector supports remote push mode

When the `HERMES_ANALYTICS_REMOTE` environment variable is set, the system SHALL POST the generated snapshot JSON to `{HERMES_ANALYTICS_REMOTE}/api/snapshots` instead of writing to a local file.

#### Scenario: Remote push enabled and successful

- **WHEN** `HERMES_ANALYTICS_REMOTE` is set to `https://hermes-dash.example.com` and the remote server accepts the POST
- **THEN** the collector sends the snapshot via HTTP POST with Content-Type application/json and prints a success message

#### Scenario: Remote push fails

- **WHEN** `HERMES_ANALYTICS_REMOTE` is set but the remote server is unreachable or returns a non-2xx status
- **THEN** the collector falls back to writing `snapshot_latest.json` locally and logs the error

### Requirement: Remote push uses requests library

The system SHALL import the `requests` library only when `HERMES_ANALYTICS_REMOTE` is set, keeping it as an optional dependency.

#### Scenario: requests not installed and remote push enabled

- **WHEN** `HERMES_ANALYTICS_REMOTE` is set but `requests` is not installed
- **THEN** the collector prints an error message: "requests library required for remote mode. Install with: pip install requests" and falls back to local mode

#### Scenario: requests not installed and remote push not enabled

- **WHEN** `HERMES_ANALYTICS_REMOTE` is not set and `requests` is not installed
- **THEN** the collector runs normally in local mode with no import error

### Requirement: Local mode is the default

When `HERMES_ANALYTICS_REMOTE` is not set, the system SHALL write `snapshot_latest.json` to the current working directory.

#### Scenario: Default behavior

- **WHEN** no special environment variables are set
- **THEN** `snapshot_latest.json` is written to `./snapshot_latest.json`
