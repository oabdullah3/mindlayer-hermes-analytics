## ADDED Requirements

### Requirement: Session header with metadata

The dashboard SHALL display the session's key metadata at the top of the detail page.

#### Scenario: Session is found in the snapshot

- **WHEN** the user navigates to a session detail page with a valid `session_id`
- **THEN** the dashboard renders the session's `model`, `platform`, `chat_name`, `started_at`, `ended_at`, computed `duration`, and `session_id`

#### Scenario: Session not found

- **WHEN** the provided `session_id` does not exist in the snapshot
- **THEN** the dashboard displays "Session not found" with a link back to the session overview

### Requirement: Token usage breakdown

The dashboard SHALL display token usage statistics for the session.

#### Scenario: Session has token data

- **WHEN** the session contains a `tokens` object
- **THEN** the dashboard renders token metrics: input tokens, output tokens, total tokens, and token breakdown if available

#### Scenario: Session missing token data

- **WHEN** the session does not contain `tokens`
- **THEN** the dashboard displays "No token data available" for the token section

### Requirement: Skills loaded table

The dashboard SHALL display a table of all skills loaded during the session.

#### Scenario: Session has skills loaded

- **WHEN** the session's `skills_loaded` array is non-empty
- **THEN** the dashboard renders a table with columns: `skill_name`, `content_chars`, `token_estimate`, `preceding_user_message` (truncated to 100 chars), and `load_timestamp`

#### Scenario: No skills loaded in session

- **WHEN** the session's `skills_loaded` array is empty
- **THEN** the dashboard displays "No skills loaded in this session"

### Requirement: Tool calls table

The dashboard SHALL display a table of all tool calls made during the session.

#### Scenario: Session has tool calls

- **WHEN** the session's `tool_calls` array is non-empty
- **THEN** the dashboard renders a table with columns: `tool_name`, `count`, and `message_ids` (count displayed as a badge)

#### Scenario: No tool calls in session

- **WHEN** the session's `tool_calls` array is empty
- **THEN** the dashboard displays "No tool calls in this session"

### Requirement: Shell commands table

The dashboard SHALL display a table of shell commands executed during the session.

#### Scenario: Session has shell commands

- **WHEN** the session's `shell_commands` array is non-empty
- **THEN** the dashboard renders a table showing each command and its timestamp

#### Scenario: No shell commands in session

- **WHEN** the session's `shell_commands` array is empty
- **THEN** the dashboard displays "No shell commands in this session"

### Requirement: User messages list

The dashboard SHALL display the user messages from the session.

#### Scenario: Session has user messages

- **WHEN** the session's `user_messages` array is non-empty
- **THEN** the dashboard renders a scrollable list of messages with timestamps

#### Scenario: No user messages in session

- **WHEN** the session's `user_messages` array is empty
- **THEN** the dashboard displays "No user messages in this session"

### Requirement: Errors list

The dashboard SHALL display any errors that occurred during the session.

#### Scenario: Session has errors

- **WHEN** the session's `errors` array is non-empty
- **THEN** the dashboard renders errors in a highlighted/styled section distinct from normal data

#### Scenario: No errors in session

- **WHEN** the session's `errors` array is empty
- **THEN** the errors section displays "No errors" or is hidden

### Requirement: Skills vs tools visual breakdown

The dashboard SHALL display a visual comparison of skills loaded vs tool calls.

#### Scenario: Session has both skills and tools

- **WHEN** the session has both `skills_loaded` and `tool_calls` data
- **THEN** the dashboard renders a side-by-side or grouped visualization comparing skill load count and tool call count
