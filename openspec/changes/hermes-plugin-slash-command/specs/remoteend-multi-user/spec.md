## ADDED Requirements

### Requirement: remoteend directory contains multi-user server

A new `remoteend/` top-level directory SHALL contain `server.py` — a Flask REST API server with multi-user flat-file persistence.

#### Scenario: Server stores per-user snapshots
- **WHEN** a collector POSTs a snapshot with `"username": "alice"`
- **THEN** the server writes the snapshot to `remoteend/server_data/alice/snapshot_{timestamp}.json`

#### Scenario: Server serves multi-user snapshot listing
- **WHEN** `GET /api/snapshots/latest` is called
- **THEN** the response includes all users' latest snapshots in a `{"snapshots": {"alice": {...}, "bob": {...}}}` structure

#### Scenario: Server serves per-user endpoints
- **WHEN** `GET /api/users` is called
- **THEN** the response lists all usernames that have pushed snapshots

### Requirement: remoteend dashboard has user filter

The remote multi-user Streamlit dashboard SHALL include a user filter dropdown.

#### Scenario: User filter available
- **WHEN** the remote dashboard is loaded
- **THEN** a "Select User" dropdown is visible, populated from `GET /api/users`
- **AND** selecting a user filters all dashboard views to that user's data

#### Scenario: All users view
- **WHEN** "All Users" is selected in the dropdown
- **THEN** dashboard metrics aggregate across all users

### Requirement: remoteend dashboard has user leaderboard page

The remote dashboard SHALL include a "Users" page showing comparative metrics.

#### Scenario: Users page displays rankings
- **WHEN** the Users page is loaded
- **THEN** a leaderboard table ranks users by session count, skill loads, and tool calls
- **AND** each user row shows total tokens and most-used model

#### Scenario: Clicking a user drills down
- **WHEN** a user row is clicked
- **THEN** the dashboard navigates to a filtered Session Overview showing only that user's sessions

### Requirement: Remote server and dashboard start independently

The `remoteend/` server and dashboard SHALL be started by the operator, not by the slash command.

#### Scenario: Starting remote server
- **WHEN** an operator runs `python3 remoteend/server.py`
- **THEN** the Flask server starts on `PORT` (default 5555) with multi-user persistence

#### Scenario: Starting remote dashboard
- **WHEN** an operator runs `streamlit run remoteend/dashboard.py`
- **THEN** the Streamlit dashboard starts on port 8501, reading from the remote server's API

### Requirement: Remote dashboard has no shutdown button

The remote dashboard SHALL NOT include a "Shutdown Analytics" button, as it is a persistent service.

#### Scenario: Remote dashboard sidebar
- **WHEN** the remote dashboard is loaded
- **THEN** the sidebar does not contain a shutdown button
- **AND** does not reference PID files
