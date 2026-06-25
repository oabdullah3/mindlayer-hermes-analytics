## ADDED Requirements

### Requirement: Skills ranking table

The dashboard SHALL display a table of all skills ranked by load count.

#### Scenario: Skills exist in global insights

- **WHEN** `global_insights.skills` is non-empty
- **THEN** the dashboard renders a table with columns: `rank`, `name`, `load_count`, `total_chars`, `token_estimate`, and computed `avg_chars_per_load` and `avg_tokens_per_load`

#### Scenario: No skills in global insights

- **WHEN** `global_insights.skills` is empty or missing
- **THEN** the dashboard computes the ranking from sessions' `skills_loaded` arrays and displays it

#### Scenario: No skills data at all

- **WHEN** no sessions contain `skills_loaded` data
- **THEN** the dashboard displays "No skills data available"

### Requirement: Skills usage bar chart

The dashboard SHALL display a horizontal bar chart of the top N skills by load count.

#### Scenario: More than 10 skills

- **WHEN** more than 10 skills are present
- **THEN** the dashboard shows the top 10 skills in a bar chart with an option to show all

#### Scenario: 10 or fewer skills

- **WHEN** the number of skills is 10 or fewer
- **THEN** the dashboard shows all skills in the bar chart

### Requirement: Token estimate distribution

The dashboard SHALL display the distribution of token estimates across skills.

#### Scenario: Skills have token estimates

- **WHEN** skills have non-zero `token_estimate` values
- **THEN** the dashboard renders a histogram or box plot showing the distribution of token estimates

### Requirement: Skills usage timeline

The dashboard SHALL display a timeline of skill loads over time.

#### Scenario: Skills have load timestamps

- **WHEN** skill load entries contain timestamps
- **THEN** the dashboard renders a timeline chart showing skill loads per day, with each skill as a separate series

### Requirement: Preceding user messages analysis

The dashboard SHALL display the most common preceding user messages that trigger skill loads.

#### Scenario: Skills have preceding user messages

- **WHEN** skill load entries contain `preceding_user_message`
- **THEN** the dashboard renders a table of the most frequent preceding messages with their counts, truncated for display

### Requirement: Skill drill-down to sessions

The dashboard SHALL allow clicking a skill name to see which sessions loaded that skill.

#### Scenario: User clicks a skill name

- **WHEN** the user clicks on a skill in the ranking table
- **THEN** the dashboard displays a filtered list of sessions that loaded that skill, showing session ID, date, platform, and the preceding message that triggered the load
