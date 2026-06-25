## ADDED Requirements

### Requirement: Session list with key metrics

The dashboard SHALL display a table listing all sessions from the snapshot with key summary columns.

#### Scenario: Sessions exist in the snapshot

- **WHEN** the snapshot contains sessions
- **THEN** the dashboard renders a table with columns: `session_id`, `model`, `platform`, `started_at`, `duration` (computed from `ended_at - started_at`), `token_count`, `skill_loads_count`, `tool_calls_count`, `user_messages_count`

#### Scenario: No sessions in the snapshot

- **WHEN** the snapshot has zero sessions or is unavailable
- **THEN** the dashboard displays an empty-state message: "No sessions found. Run the collector to generate data."

### Requirement: Aggregate summary cards

The dashboard SHALL display aggregate summary metrics at the top of the page.

#### Scenario: Snapshot with session data

- **WHEN** the snapshot contains sessions and global_insights
- **THEN** the dashboard renders summary cards showing: total sessions, total messages, total skill loads, total tool calls, unique models used, unique platforms

#### Scenario: Snapshot without global_insights

- **WHEN** the snapshot has sessions but `global_insights` is missing or empty
- **THEN** the dashboard computes aggregates from the session list and displays them

### Requirement: Session filtering

The dashboard SHALL allow filtering sessions by model and platform.

#### Scenario: User selects a model filter

- **WHEN** the user selects a specific model from a dropdown
- **THEN** the session table and summary cards update to show only sessions matching that model

#### Scenario: User selects a platform filter

- **WHEN** the user selects a platform from a dropdown
- **THEN** the session table and summary cards update to show only sessions matching that platform

#### Scenario: User clears all filters

- **WHEN** the user resets filters to "All"
- **THEN** all sessions are shown

### Requirement: Session timeline chart

The dashboard SHALL display a timeline chart showing session activity over time.

#### Scenario: Sessions span multiple dates

- **WHEN** the snapshot has sessions across multiple dates
- **THEN** the dashboard renders a bar chart or line chart with date on the x-axis and session count on the y-axis

#### Scenario: All sessions on a single date

- **WHEN** all sessions fall within one calendar date
- **THEN** the chart shows a single bar or point for that date

### Requirement: Model distribution chart

The dashboard SHALL display the distribution of sessions by model.

#### Scenario: Multiple models used

- **WHEN** sessions use different models
- **THEN** the dashboard renders a horizontal bar chart with model names and session counts

### Requirement: Session row click navigates to session detail

The dashboard SHALL allow clicking a session row to navigate to the session detail page.

#### Scenario: User clicks a session in the table

- **WHEN** the user clicks on a session row
- **THEN** the dashboard navigates to the session detail page for that session, passing the `session_id`
