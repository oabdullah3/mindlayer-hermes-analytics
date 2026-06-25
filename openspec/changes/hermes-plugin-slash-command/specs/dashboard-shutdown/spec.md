## ADDED Requirements

### Requirement: Dashboard has a shutdown button in the sidebar

The local single-user Streamlit dashboard SHALL include a "🛑 Shutdown Analytics" button in the sidebar.

#### Scenario: Button is visible
- **WHEN** the local dashboard is loaded
- **THEN** a red "🛑 Shutdown Analytics" button appears in the sidebar
- **AND** explanatory text below reads: "Closes the analytics server and this dashboard. Your data is preserved."

#### Scenario: Button is only in local dashboard
- **WHEN** the remote multi-user dashboard (`remoteend/dashboard.py`) is loaded
- **THEN** no "Shutdown Analytics" button appears (remote dashboard is persistent)

### Requirement: Shutdown button kills server process

When the "🛑 Shutdown Analytics" button is clicked, the dashboard SHALL terminate the Flask server subprocess.

#### Scenario: Button clicked
- **WHEN** the user clicks "🛑 Shutdown Analytics"
- **THEN** the dashboard reads the server PID from `/tmp/hermes-analytics-server.pid`
- **AND** sends SIGTERM to that PID
- **AND** if the process doesn't exit within 5 seconds, sends SIGKILL

#### Scenario: PID file is missing
- **WHEN** the server PID file does not exist at `/tmp/hermes-analytics-server.pid`
- **THEN** the dashboard logs a warning and continues with shutdown of remaining processes

### Requirement: Shutdown button stops the dashboard itself

After killing the server, the dashboard SHALL terminate itself.

#### Scenario: Dashboard stops
- **WHEN** the server process has been terminated
- **THEN** `st.stop()` is called, ending the Streamlit session
- **AND** the dashboard PID file `/tmp/hermes-analytics-dashboard.pid` is removed

#### Scenario: Closing browser tab does NOT shut down
- **WHEN** the user closes the browser tab without clicking the shutdown button
- **THEN** both the Flask server and Streamlit dashboard continue running
- **AND** the user can reconnect by opening `http://localhost:{port}` again

### Requirement: Shutdown button shows confirmation

The dashboard SHALL show a success message after shutdown completes.

#### Scenario: Shutdown successful
- **WHEN** all processes are terminated
- **THEN** the dashboard displays: "✅ Analytics shut down. You may close this tab."
- **AND** all PID files are cleaned up
