## ADDED Requirements

### Requirement: Tools ranking table

The dashboard SHALL display a table of all tools ranked by call count.

#### Scenario: Tools exist in global insights

- **WHEN** `global_insights.tools` is non-empty
- **THEN** the dashboard renders a table with columns: `rank`, `name`, `call_count`, and `percentage_of_total` (computed as call_count / total_calls * 100)

#### Scenario: No tools in global insights

- **WHEN** `global_insights.tools` is empty or missing
- **THEN** the dashboard computes the ranking from sessions' `tool_calls` arrays and displays it

#### Scenario: No tools data at all

- **WHEN** no sessions contain `tool_calls` data
- **THEN** the dashboard displays "No tools data available"

### Requirement: Tools usage bar chart

The dashboard SHALL display a horizontal bar chart of tools by call count.

#### Scenario: Tools data available

- **WHEN** tools data is present
- **THEN** the dashboard renders a horizontal bar chart with tool names on the y-axis and call counts on the x-axis

### Requirement: Tools distribution pie chart

The dashboard SHALL display a pie or donut chart showing the proportion of calls per tool.

#### Scenario: Multiple tools with different call counts

- **WHEN** more than one tool exists
- **THEN** the dashboard renders a pie chart showing each tool's share of total calls

#### Scenario: Single tool

- **WHEN** only one tool exists in the data
- **THEN** the pie chart shows 100% for that tool

### Requirement: Tools usage timeline

The dashboard SHALL display a timeline of tool calls over time.

#### Scenario: Sessions with tool calls span multiple dates

- **WHEN** sessions containing tool calls span multiple dates
- **THEN** the dashboard renders a timeline chart showing tool calls per day, with each tool as a separate series

### Requirement: Session-tool correlation

The dashboard SHALL display which sessions use which tools.

#### Scenario: Tools are linked to sessions

- **WHEN** session `tool_calls` entries are present
- **THEN** the dashboard renders a heatmap or cross-tabulation showing tool usage across sessions, with sessions on one axis and tools on the other

### Requirement: Tool drill-down to sessions

The dashboard SHALL allow clicking a tool name to see which sessions used that tool.

#### Scenario: User clicks a tool name

- **WHEN** the user clicks on a tool in the ranking table
- **THEN** the dashboard displays a filtered list of sessions that called that tool, showing session ID, date, model, and call count

### Requirement: Tool call count distribution

The dashboard SHALL display the distribution of tool call counts per session.

#### Scenario: Sessions have varying tool call counts

- **WHEN** sessions have different tool call counts
- **THEN** the dashboard renders a histogram showing the distribution of tool call counts (e.g., how many sessions have 0-5 calls, 6-10 calls, etc.)
