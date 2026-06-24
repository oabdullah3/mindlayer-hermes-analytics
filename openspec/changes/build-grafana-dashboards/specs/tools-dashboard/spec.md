## ADDED Requirements

### Requirement: Tool Call Leaderboard panel

The tools dashboard SHALL include a bar gauge panel displaying all tools ranked by call count over the selected time range.

#### Scenario: Tools called in selected time range

- **WHEN** tools have been called in sessions within the time range
- **THEN** the bar gauge shows tool names and call counts, sorted descending

### Requirement: Tool Call Timeline panel

The tools dashboard SHALL include a time series panel showing tool calls per day, stacked by tool name.

#### Scenario: Tool calls across multiple days

- **WHEN** tools are called across multiple days
- **THEN** the time series shows daily data points stacked by tool name

### Requirement: Tool Execution Duration table

The tools dashboard SHALL include a table panel with columns: tool name, call count, average duration, maximum duration (from log_payloads data when available).

#### Scenario: Duration data available from log_payloads

- **WHEN** log_payloads JSON files exist and contain duration_ms for tool executions
- **THEN** the table displays avg and max duration per tool

#### Scenario: No log_payloads data

- **WHEN** log_payloads directory does not exist or is empty
- **THEN** the duration columns show "N/A" or are hidden

### Requirement: Tool Errors stat panel

The tools dashboard SHALL include a stat panel showing the total number of tool errors and error rate as a percentage.

#### Scenario: Errors exist in agent.log

- **WHEN** errors have been parsed from agent.log
- **THEN** the stat panel displays the total error count and error rate percentage

#### Scenario: No errors

- **WHEN** no errors exist in the time range
- **THEN** the stat panel displays "0" with a green indicator

### Requirement: Tool Co-occurrence Heatmap

The tools dashboard SHALL include a heatmap panel showing which tools are called together in the same session as a matrix.

#### Scenario: Multiple tools used in same sessions

- **WHEN** sessions contain calls to multiple different tools
- **THEN** the heatmap shows a symmetric matrix with tool names on both axes and co-occurrence counts in cells

### Requirement: Terminal Usage Breakdown pie chart

The tools dashboard SHALL include a pie chart panel showing the breakdown of terminal tool outcomes: success, error, timeout.

#### Scenario: Mixed terminal outcomes

- **WHEN** terminal tool calls include both successful and failed executions
- **THEN** the pie chart shows slices for each outcome category
