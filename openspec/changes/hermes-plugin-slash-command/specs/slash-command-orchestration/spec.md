## ADDED Requirements

### Requirement: Slash command starts local server

The `/hermes-snapshot-analytics` slash command handler SHALL start a local Flask server as a subprocess before collecting the snapshot.

#### Scenario: Server starts successfully
- **WHEN** the slash command is invoked
- **THEN** a Flask server subprocess is spawned on `HERMES_ANALYTICS_SERVER_PORT` (default 5555)
- **AND** the server PID is written to `/tmp/hermes-analytics-server.pid`
- **AND** the handler waits up to 3 seconds for the server to become healthy

#### Scenario: Server port is occupied
- **WHEN** the default server port is already in use
- **THEN** the handler increments the port number until finding a free port
- **AND** the actual port used is reported in the response

#### Scenario: Server fails to start
- **WHEN** the Flask server subprocess exits with an error within the startup window
- **THEN** the handler returns an error message: "Failed to start analytics server: <reason>"
- **AND** no dashboard is started

### Requirement: Slash command runs the collector

After the server starts, the slash command handler SHALL run the collector to generate a snapshot and push it to available destinations.

#### Scenario: Collector runs successfully
- **WHEN** the local server is healthy
- **THEN** the collector reads Hermes data from `~/.hermes/`
- **AND** POSTs the snapshot to the local server at `http://localhost:{port}/api/snapshots`
- **AND** if `HERMES_ANALYTICS_REMOTE` is set, also POSTs to that URL
- **AND** always writes `snapshot_latest.json` locally as a fallback

#### Scenario: Collector fails
- **WHEN** the collector encounters an error (e.g., missing state.db)
- **THEN** the handler returns an error message describing the failure
- **AND** the local server is stopped (cleanup)

### Requirement: Slash command starts local dashboard

After the collector completes, the handler SHALL start a Streamlit dashboard subprocess.

#### Scenario: Dashboard starts successfully
- **WHEN** the collector finishes successfully
- **THEN** a Streamlit subprocess is spawned on `HERMES_ANALYTICS_DASHBOARD_PORT` (default 8501)
- **AND** the dashboard PID is written to `/tmp/hermes-analytics-dashboard.pid`
- **AND** the handler returns a message with the dashboard URL

#### Scenario: Dashboard port is occupied
- **WHEN** the default dashboard port is already in use
- **THEN** the handler increments the port number until finding a free port
- **AND** the URL returned to the user reflects the actual port

### Requirement: Slash command returns dashboard URL to user

The slash command handler SHALL return a message containing the dashboard URL.

#### Scenario: Successful orchestration
- **WHEN** server, collector, and dashboard all succeed
- **THEN** the response is: "✅ Hermes Analytics is ready! Dashboard: http://localhost:{port}\n\nUse the 🛑 Shutdown button in the dashboard sidebar to stop all analytics processes."

#### Scenario: Remote server URL available
- **WHEN** `HERMES_ANALYTICS_REMOTE` is configured
- **THEN** the response also includes: "📊 Company dashboard: {HERMES_ANALYTICS_REMOTE}"

#### Scenario: No data available
- **WHEN** the collector finds no sessions in `~/.hermes/`
- **THEN** the response is: "⚠️ Hermes Analytics started but no session data found. Dashboard: http://localhost:{port}"

### Requirement: Slash command cleans up on Hermes session end

When the Hermes session that invoked the slash command ends, the spawned server and dashboard processes SHALL be terminated.

#### Scenario: Session ends
- **WHEN** the Hermes session ends (user exits CLI or gateway disconnects)
- **THEN** the handler's cleanup logic sends SIGTERM to the PIDs in `/tmp/hermes-analytics-server.pid` and `/tmp/hermes-analytics-dashboard.pid`
