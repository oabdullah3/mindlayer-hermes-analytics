## ADDED Requirements

### Requirement: Synthetic state.db contains sessions table with known data

The test fixture SHALL create a `state.db` with a `sessions` table matching the Hermes schema and SHALL insert at least 3 sessions with distinct platforms, models, token counts, and message counts.

#### Scenario: Fixture database is created and queryable

- **WHEN** the test fixture is initialized
- **THEN** `state.db` exists, has a `sessions` table with the documented Hermes schema, and `SELECT COUNT(*) FROM sessions` returns 3 or more

#### Scenario: Sessions span multiple platforms

- **WHEN** the fixture sessions are queried
- **THEN** at least one session has `source = 'telegram'`, at least one has `source = 'discord'`, and at least one has `source = 'cli'`

#### Scenario: Sessions have token counts

- **WHEN** the fixture sessions are inspected
- **THEN** each session has non-zero `input_tokens` and `output_tokens`, and at least one session has non-zero `cache_read_tokens` and `reasoning_tokens`

### Requirement: Synthetic state.db contains messages table with all roles

The test fixture SHALL create a `messages` table and SHALL insert messages of all three roles (user, assistant, tool) across sessions, including assistant messages with `tool_calls` JSON for `skill_view` invocations.

#### Scenario: All message roles present

- **WHEN** the fixture messages are queried
- **THEN** `SELECT DISTINCT role FROM messages` returns `user`, `assistant`, and `tool`

#### Scenario: Skill load messages present

- **WHEN** the fixture messages are queried
- **THEN** at least one assistant message has `tool_calls` JSON containing `{"function": {"name": "skill_view"}}` and a corresponding tool message exists with `tool_name = 'skill_view'` and matching `tool_call_id`

#### Scenario: Multiple tool types present

- **WHEN** the fixture messages are queried
- **THEN** `SELECT DISTINCT tool_name FROM messages WHERE role = 'tool'` includes at least `skill_view`, `terminal`, and `browser_navigate`

### Requirement: Synthetic state.db includes preceding user messages before skill loads

For each skill load in the fixture, the message immediately before it (by `id - 1` within the same `session_id`) SHALL be a user message.

#### Scenario: Skill load has preceding user message

- **WHEN** a skill_load assistant message exists at id N
- **THEN** the message at id N-1 in the same session has `role = 'user'` and non-empty `content`

### Requirement: Fixture database file is created in a temporary directory

The fixture SHALL create `state.db` in a pytest `tmp_path` so it is isolated from the real filesystem and cleaned up after each test run.

#### Scenario: Fixture uses temp directory

- **WHEN** the test fixture is invoked
- **THEN** `state.db` is created in a `tmp_path` and does not touch `~/.hermes/` or any real path
