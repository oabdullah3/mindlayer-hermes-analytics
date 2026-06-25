# Data Extraction (delta)

**This is a delta spec.** It modifies the base spec at `openspec/specs/data-extraction/spec.md`.

## MODIFIED Requirements

### Requirement: Collector reads session list from state.db

The system SHALL query the `sessions` table from `~/.hermes/state.db` (or `$HERMES_HOME/state.db`) and return all sessions ordered by `started_at` descending. The returned session dictionary SHALL include the `title` column mapped to `chat_name`.

#### Scenario: Successful session list query

- **WHEN** state.db exists and contains session rows
- **THEN** collector returns a list of dictionaries with keys: id, source, user_id, model, title, started_at, ended_at, ended_reason, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens, estimated_cost_usd, message_count, tool_call_count

#### Scenario: Session title is populated

- **WHEN** a session row has a non-null `title` value
- **THEN** the snapshot's `chat_name` field contains that title value

#### Scenario: Session title is null

- **WHEN** a session row has a null `title` value
- **THEN** the snapshot's `chat_name` field is null

#### Scenario: Empty state.db

- **WHEN** state.db exists but has no rows in the sessions table
- **THEN** collector returns an empty list and produces a valid snapshot with zero sessions

#### Scenario: Missing state.db

- **WHEN** state.db does not exist at the configured path
- **THEN** collector exits with a non-zero status and prints an error message to stderr

### Requirement: Collector aggregates tool calls per session

The system SHALL aggregate tool calls per session by parsing the `tool_calls` JSON column from assistant messages (role='assistant'), extracting `function.name` for each tool call object, and counting occurrences. For an assistant message with no `tool_calls`, it is skipped. For assistant messages with N tool calls in the JSON array, the collector SHALL count each `function.name` as one invocation, then match the N subsequent tool-response rows (role='tool') by position to determine success/failure status.

#### Scenario: Single tool call per assistant message

- **WHEN** an assistant message has `tool_calls` containing one function call `{"function": {"name": "terminal"}}`
- **THEN** the collector counts `terminal` once and checks the next tool-response row for success status

#### Scenario: Multiple batched tool calls per assistant message

- **WHEN** an assistant message has `tool_calls` containing two function calls `{"function": {"name": "terminal"}}` and `{"function": {"name": "search"}}`
- **THEN** the collector counts `terminal` once and `search` once, and checks the next two tool-response rows positionally for their respective success status

#### Scenario: Tool calls JSON is null or empty

- **WHEN** an assistant message has null or empty `tool_calls`
- **THEN** the collector skips that message with no tool counts added

#### Scenario: Tool calls JSON is malformed

- **WHEN** an assistant message has `tool_calls` that cannot be parsed as JSON
- **THEN** the collector logs a warning and skips that message

#### Scenario: Multiple tools called across a session

- **WHEN** a session has assistant messages calling "terminal", "browser_navigate", and "skill_view"
- **THEN** the session's `tool_calls` list contains one entry per unique tool name with count and aggregated success rate

#### Scenario: No tool calls in session

- **WHEN** a session has no assistant messages with non-null `tool_calls`
- **THEN** the session's `tool_calls` list is empty
