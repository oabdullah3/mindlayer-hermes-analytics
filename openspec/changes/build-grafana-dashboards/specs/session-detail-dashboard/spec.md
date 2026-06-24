## ADDED Requirements

### Requirement: Session Header panel

The session detail dashboard SHALL include a text or stat panel displaying the session's metadata: session ID, platform, model, start time, duration, and chat name.

#### Scenario: Session detail loaded

- **WHEN** a session is selected via dashboard linking or variable dropdown
- **THEN** the header panel displays all session metadata fields

### Requirement: Token Breakdown bar gauge

The session detail dashboard SHALL include a bar gauge panel showing the token breakdown for the selected session: input, output, cache read, cache write, reasoning tokens.

#### Scenario: Session has token data

- **WHEN** the selected session has token values
- **THEN** the bar gauge shows a horizontal bar for each token category with the count

### Requirement: Skills Loaded table

The session detail dashboard SHALL include a table panel listing skills loaded in the selected session with columns: skill name, load timestamp, preceding user message (truncated to 100 chars).

#### Scenario: Session has skill loads

- **WHEN** the session's skills_loaded array is populated
- **THEN** the table shows one row per skill with all columns

#### Scenario: Session has no skill loads

- **WHEN** skills_loaded is empty
- **THEN** the table displays "No skills loaded in this session"

### Requirement: Tool Calls bar chart

The session detail dashboard SHALL include a bar chart panel showing tool calls in the selected session, one bar per tool with call count.

#### Scenario: Session has tool calls

- **WHEN** the session's tool_calls array is populated
- **THEN** the bar chart shows tool names on x-axis and call counts on y-axis

### Requirement: User Messages table

The session detail dashboard SHALL include a table panel listing user messages in the selected session with columns: message ID, timestamp, content (truncated to 200 chars).

#### Scenario: Session has user messages

- **WHEN** the session's user_messages array has entries
- **THEN** the table shows each user message chronologically

### Requirement: Errors log panel

The session detail dashboard SHALL include a logs panel displaying errors associated with the selected session.

#### Scenario: Session has errors

- **WHEN** the session's errors array is populated
- **THEN** the logs panel displays each error with timestamp and message

#### Scenario: Session has no errors

- **WHEN** errors array is empty
- **THEN** the logs panel displays "No errors" or is hidden
