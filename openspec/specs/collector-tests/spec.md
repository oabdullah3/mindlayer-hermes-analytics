## ADDED Requirements

### Requirement: Collector test verifies session count and metadata

The collector test SHALL run the collector against the fixture database and assert that the snapshot contains the expected number of sessions, each with correct platform, model, and token values.

#### Scenario: Session count matches fixture

- **WHEN** the collector runs against the fixture database with 3 sessions
- **THEN** `len(snapshot['sessions'])` equals 3

#### Scenario: Session tokens are extracted correctly

- **WHEN** the collector extracts session data
- **THEN** each session's `tokens` dict has the same values as the fixture's sessions table row

### Requirement: Collector test verifies skill load detection

The collector test SHALL assert that skill loads are detected correctly: the right number per session, correct skill names extracted from tool response content, and correct load timestamps.

#### Scenario: Skills detected in sessions that have them

- **WHEN** the collector runs against the fixture (which has skill loads in sessions 1 and 3)
- **THEN** session 1 has 2 skills_loaded entries, session 2 has 0, session 3 has 1

#### Scenario: Skill names are parsed correctly

- **WHEN** skill loads are extracted from tool response content JSON
- **THEN** each `skill_name` field matches the name in the fixture's tool response content

### Requirement: Collector test verifies preceding user message resolution

The collector test SHALL assert that each skill load has a `preceding_user_message` field containing the content of the user message immediately before the skill load.

#### Scenario: Preceding user message is present

- **WHEN** a skill load in the fixture has a preceding user message
- **THEN** the collector's `preceding_user_message` field for that skill load is non-null and matches the fixture's user message content

### Requirement: Collector test verifies tool call aggregation

The collector test SHALL assert that tool calls are aggregated correctly per session: unique tool names, correct counts, and message_ids arrays.

#### Scenario: Tool calls aggregated per session

- **WHEN** the collector aggregates tool calls for session 1 (which has 5 tool calls across 3 tool types in the fixture)
- **THEN** session 1's `tool_calls` list has 3 entries, each with correct `count` and `message_ids` length matching the count

### Requirement: Collector test verifies token estimation math

The collector test SHALL assert that `token_estimate = CEIL(LENGTH(content) / 4)` is computed correctly for each skill load.

#### Scenario: Token estimate is computed

- **WHEN** a skill load has content of known length (e.g., 100 chars)
- **THEN** `token_estimate` equals `CEIL(100 / 4) = 25`

### Requirement: Collector test verifies global insights

The collector test SHALL assert that `global_insights` contains correct totals (total_sessions, total_messages, total_skill_loads) and ranked skills/tools leaderboards matching the fixture data.

#### Scenario: Global insights computed from fixture

- **WHEN** the collector runs against the fixture
- **THEN** `global_insights.total_sessions` equals 3, `global_insights.total_skill_loads` equals 3, and the skills/tools leaderboards are sorted by count descending

### Requirement: Collector test handles missing optional data sources gracefully

The collector test SHALL assert that the collector does not crash when `agent.log` or `log_payloads/` do not exist in the fixture directory.

#### Scenario: agent.log missing

- **WHEN** the fixture's `HERMES_HOME` has no `logs/agent.log`
- **THEN** the collector completes successfully with empty `errors` arrays in all sessions
