## ADDED Requirements

### Requirement: Collector reads session list from state.db

The system SHALL query the `sessions` table from `~/.hermes/state.db` (or `$HERMES_HOME/state.db`) and return all sessions ordered by `started_at` descending.

#### Scenario: Successful session list query

- **WHEN** state.db exists and contains session rows
- **THEN** collector returns a list of dictionaries with keys: id, source, user_id, model, started_at, ended_at, ended_reason, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens, estimated_cost_usd, message_count, tool_call_count

#### Scenario: Empty state.db

- **WHEN** state.db exists but has no rows in the sessions table
- **THEN** collector returns an empty list and produces a valid snapshot with zero sessions

#### Scenario: Missing state.db

- **WHEN** state.db does not exist at the configured path
- **THEN** collector exits with a non-zero status and prints an error message to stderr

### Requirement: Collector detects skill loads from messages

The system SHALL query the `messages` table for assistant messages where `tool_calls` JSON contains function calls to `skill_view` or `skill_manage`, then fetch the corresponding tool response to extract the skill name from `content`.

#### Scenario: Skill load detected via skill_view

- **WHEN** an assistant message has `tool_calls` containing `{"function": {"name": "skill_view"}}` and a matching tool response exists with `tool_name = 'skill_view'`
- **THEN** the collector extracts the skill name from the tool response's `content` JSON field and records: skill_name, load_message_id, load_timestamp, tool_call_id, content_chars, token_estimate

#### Scenario: No skill loads in session

- **WHEN** an assistant message has no `tool_calls` referencing `skill_view` or `skill_manage`
- **THEN** the session's `skills_loaded` list is empty

#### Scenario: Orphaned assistant message without tool response

- **WHEN** an assistant message references a `tool_call_id` that has no matching tool response
- **THEN** the collector skips that skill load and logs a warning

### Requirement: Collector fetches preceding user message for each skill load

The system SHALL query the message immediately before each skill load (by `id - 1` within the same `session_id`) and include its content as `preceding_user_message`.

#### Scenario: Preceding message is a user message

- **WHEN** `messages.id = skill_load_msg_id - 1` exists and has `role = 'user'`
- **THEN** the collector records `preceding_user_message` with the user message content

#### Scenario: Preceding message is not a user message

- **WHEN** `messages.id = skill_load_msg_id - 1` exists but has `role != 'user'` (e.g., tool response)
- **THEN** the collector records `preceding_user_message` as null or empty

#### Scenario: No preceding message

- **WHEN** the skill load is the first message in the session (no id-1 message)
- **THEN** the collector records `preceding_user_message` as null

### Requirement: Collector aggregates tool calls per session

The system SHALL query all messages with `role = 'tool'` per session and aggregate them by `tool_name` with count and message_ids.

#### Scenario: Multiple tools called in a session

- **WHEN** a session has tool messages with names "terminal", "browser_navigate", "skill_view"
- **THEN** the session's `tool_calls` list contains one entry per unique tool_name with count and message_ids array

#### Scenario: No tool calls in session

- **WHEN** a session has no messages with `role = 'tool'`
- **THEN** the session's `tool_calls` list is empty

### Requirement: Collector estimates token count for skill content

The system SHALL compute a token estimate for each skill load as `CEIL(LENGTH(content) / 4)` where `content` is the skill_view tool response content.

#### Scenario: Skill content exists

- **WHEN** a skill_view tool response has non-empty content
- **THEN** `token_estimate` is set to `CEIL(LENGTH(content) / 4)` and `content_chars` is set to `LENGTH(content)`

#### Scenario: Skill content is empty or null

- **WHEN** a skill_view tool response has empty or null content
- **THEN** `token_estimate` is 0 and `content_chars` is 0

### Requirement: Collector collects all user messages per session

The system SHALL collect all messages with `role = 'user'` for each session, including message_id, content (truncated to 200 chars for display), and timestamp.

#### Scenario: Session has user messages

- **WHEN** a session has 5 user messages
- **THEN** the session's `user_messages` list contains 5 entries, each with message_id, content (truncated to 200 chars), and timestamp

#### Scenario: Session has no user messages

- **WHEN** a session has no messages with `role = 'user'`
- **THEN** the session's `user_messages` list is empty

### Requirement: Collector parses errors from agent.log

The system SHALL parse `~/.hermes/logs/agent.log` (or `$HERMES_HOME/logs/agent.log`) for lines matching `Tool terminal returned error`, extract the session ID from the bracketed prefix, and record the timestamp and error message.

#### Scenario: agent.log contains error lines

- **WHEN** agent.log exists and contains lines matching `[session_id] ... Tool terminal returned error (63.59s)`
- **THEN** the collector extracts session_id, timestamp, error message, and duration for each match and associates them with the corresponding session

#### Scenario: agent.log does not exist

- **WHEN** agent.log does not exist at the configured path
- **THEN** the collector logs a warning and continues; no errors are recorded

#### Scenario: agent.log has no error lines

- **WHEN** agent.log exists but contains no `Tool terminal returned error` lines
- **THEN** the `errors` list for all sessions is empty

### Requirement: Collector produces global insights

The system SHALL compute aggregate statistics across all sessions: total_sessions, total_messages, total_skill_loads, skills leaderboard (by load_count with total_chars and token_estimate), and tools leaderboard (by call_count).

#### Scenario: Multiple sessions with skills and tools

- **WHEN** the snapshot contains sessions with skill loads and tool calls
- **THEN** `global_insights` contains correct totals and ranked lists

#### Scenario: No sessions

- **WHEN** state.db returns zero sessions
- **THEN** `global_insights` contains zero totals and empty leaderboards
