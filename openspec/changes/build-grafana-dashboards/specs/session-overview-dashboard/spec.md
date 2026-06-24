## ADDED Requirements

### Requirement: Session Count stat panel

The session overview dashboard SHALL include a stat panel displaying the total number of sessions in the selected time range.

#### Scenario: Sessions exist

- **WHEN** sessions fall within the selected time range
- **THEN** the stat panel displays the count as a large number

### Requirement: Token Consumption time series

The session overview dashboard SHALL include a time series panel showing input and output tokens per day across all sessions.

#### Scenario: Token data available

- **WHEN** sessions have input_tokens and output_tokens populated
- **THEN** the time series shows two lines: input tokens and output tokens per day

### Requirement: Cost Over Time time series

The session overview dashboard SHALL include a time series panel showing estimated cost in USD per day.

#### Scenario: Cost data available

- **WHEN** sessions have estimated_cost_usd values
- **THEN** the time series shows daily cost in USD

### Requirement: Session List table with dashboard linking

The session overview dashboard SHALL include a table panel listing sessions with columns: session ID, platform, model, message count, tool call count, skill count, token total, cost. Each session ID row SHALL link to the session detail dashboard.

#### Scenario: Sessions exist

- **WHEN** sessions are loaded in the snapshot
- **THEN** the table displays one row per session with clickable session IDs that navigate to the session detail dashboard

### Requirement: Platform Split pie chart

The session overview dashboard SHALL include a pie chart panel showing the distribution of sessions by platform (telegram, discord, cli).

#### Scenario: Sessions from multiple platforms

- **WHEN** sessions have different source/platform values
- **THEN** the pie chart shows proportional slices for each platform

### Requirement: Model Usage bar gauge

The session overview dashboard SHALL include a bar gauge panel showing session counts per model.

#### Scenario: Multiple models used

- **WHEN** sessions use different models
- **THEN** the bar gauge ranks models by session count
