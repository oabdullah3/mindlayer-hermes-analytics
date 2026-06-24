## ADDED Requirements

### Requirement: Snapshot top-level keys validation

The schema test SHALL assert that the generated snapshot JSON contains all required top-level keys: `generated_at`, `hermes_home`, `sessions`, `global_insights`.

#### Scenario: All top-level keys present

- **WHEN** the collector generates a snapshot against the fixture
- **THEN** `snapshot.keys()` includes `generated_at`, `hermes_home`, `sessions`, `global_insights`

### Requirement: generated_at is ISO 8601 UTC timestamp

The schema test SHALL assert that `generated_at` is a string matching ISO 8601 format with UTC timezone.

#### Scenario: Timestamp is valid ISO 8601

- **WHEN** the snapshot is generated
- **THEN** `generated_at` matches the pattern `YYYY-MM-DDTHH:MM:SS` with `Z` or `+00:00` suffix

### Requirement: Session object has all required fields

The schema test SHALL assert that each session object contains: session_id, source, model, started_at, ended_at, tokens (with input/output/cache_read/cache_write/reasoning/estimated_cost_usd), stats (with message_count/tool_call_count), skills_loaded, tool_calls, user_messages, errors.

#### Scenario: Session object is complete

- **WHEN** a session is extracted from the fixture
- **THEN** the session dict has all required keys and sub-keys, with correct types (arrays for lists, numbers for counts, strings for identifiers)

#### Scenario: Empty arrays for sessions with no skills/tools/errors

- **WHEN** a session has no skills, no tool calls, and no errors (session 2 in fixture)
- **THEN** `skills_loaded`, `tool_calls`, `user_messages`, and `errors` are empty lists (not null or missing)

### Requirement: global_insights has correct structure

The schema test SHALL assert that `global_insights` contains: total_sessions (int), total_messages (int), total_skill_loads (int), skills (array of {name, load_count, total_chars, token_estimate}), tools (array of {name, count}).

#### Scenario: global_insights structure valid

- **WHEN** the snapshot is generated
- **THEN** `global_insights` has the documented keys with correct types, and totals are non-negative integers

### Requirement: Skill load object has all required fields

The schema test SHALL assert that each entry in `skills_loaded` contains: skill_name, load_message_id, load_timestamp, preceding_user_message, tool_call_id, content_chars, token_estimate.

#### Scenario: Skill load object is complete

- **WHEN** a skill load is extracted
- **THEN** all fields are present with correct types: strings for skill_name/tool_call_id, integer for load_message_id/content_chars/token_estimate, float for load_timestamp, string-or-null for preceding_user_message

### Requirement: Tool call object has all required fields

The schema test SHALL assert that each entry in `tool_calls` contains: tool_name, count, message_ids (array of integers).

#### Scenario: Tool call object is complete

- **WHEN** tool calls are aggregated for a session
- **THEN** each entry has tool_name (str), count (int, positive), message_ids (list of ints, length == count)
