## ADDED Requirements

### Requirement: Skill Load Leaderboard panel

The skills dashboard SHALL include a bar gauge panel displaying all skills ranked by load count over the selected time range, using the SQLite datasource or REST API endpoint.

#### Scenario: Skills exist in time range

- **WHEN** skills have been loaded in sessions within the selected time range
- **THEN** the bar gauge shows skill names on the y-axis and load counts as horizontal bars, sorted descending

#### Scenario: No skills in time range

- **WHEN** no skills were loaded in the selected time range
- **THEN** the bar gauge displays "No data" with an empty chart

### Requirement: Skill Load Timeline panel

The skills dashboard SHALL include a time series panel showing skill loads per day, stacked by skill name.

#### Scenario: Multiple skills loaded on different days

- **WHEN** skills are loaded across multiple days in the time range
- **THEN** the time series shows daily data points stacked by skill name with a legend

### Requirement: Skill Token Cost table

The skills dashboard SHALL include a table panel with columns: skill name, load count, total chars, token estimate, estimated cost in USD.

#### Scenario: Skills with content data

- **WHEN** skills have content_chars and token_estimate computed
- **THEN** the table displays all columns with numeric formatting (token_estimate as integer, cost as $X.XXXX)

### Requirement: Skill Load Histogram

The skills dashboard SHALL include a histogram panel showing the distribution of how many skills are loaded per session (0, 1, 2, ... N).

#### Scenario: Sessions with varying skill counts

- **WHEN** sessions contain 0 to 5+ skills each
- **THEN** the histogram shows bucket counts for each skill count value

### Requirement: Top Skills Weekly Trend

The skills dashboard SHALL include a time series panel showing the top 5 skills by load count, aggregated weekly.

#### Scenario: Skills loaded over multiple weeks

- **WHEN** skill data spans more than one week
- **THEN** the time series shows 5 lines (top 5 skills) with weekly data points

### Requirement: Auto vs Manual Skill Load pie chart

The skills dashboard SHALL include a pie chart panel distinguishing auto-loaded skills from explicitly user-triggered skill loads.

#### Scenario: Mix of auto and manual loads

- **WHEN** some skill loads are triggered by user messages mentioning the skill name and others are not
- **THEN** the pie chart shows two slices: "Auto-loaded" and "Manual" with counts and percentages
