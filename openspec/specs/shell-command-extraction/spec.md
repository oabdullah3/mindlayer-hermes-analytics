# Shell Command Extraction

**Purpose**: Track every shell command the Hermes agent executes — including the command text, exit code, output, and success/failure status — enabling operators to audit agent behaviour, identify frequently used commands, and detect failure patterns.

## Requirements

### Requirement: Extract shell commands from assistant messages
The system SHALL parse each assistant message's `tool_calls` JSON array and extract individual command executions for any tool function whose arguments contain a `command` key. The system SHALL support tool names `terminal` (primary), and SHALL be extensible to any tool whose arguments include `command`.

#### Scenario: Single terminal command extracted
- **WHEN** an assistant message contains `tool_calls: [{"function": {"name": "terminal", "arguments": "{\"command\": \"ls -la\"}"}}]`
- **THEN** the system extracts `command: "ls -la"`, `tool_name: "terminal"`, and links it to the assistant message's `timestamp`

#### Scenario: Multiple commands in one assistant message
- **WHEN** an assistant message contains multiple tool calls, each with a `command` key
- **THEN** the system extracts each command as a separate entry, preserving the order from the `tool_calls` array

#### Scenario: Tool call without command key is skipped
- **WHEN** an assistant message has a tool call whose arguments do not contain a `command` key (e.g., `{"url": "..."}`)
- **THEN** the system does NOT create a shell command entry for that tool call

### Requirement: Match commands with tool responses for exit codes
The system SHALL match each extracted command with its corresponding tool response message (by `session_id` and `tool_call_id`) to determine the exit code and output. The system SHALL parse three response content formats to extract exit code and output.

#### Scenario: Terminal response with exit code (format 1 — bracketed text)
- **WHEN** the tool response content is `[terminal] ran \`curl -s ...\` -> exit 0, 5 lines output`
- **THEN** the system extracts `exit_code: 0`, and `output`: the tool response content (full text)

#### Scenario: Terminal response with JSON output (format 2 — JSON)
- **WHEN** the tool response content is `{"output": "stdout content here", "stdout": "more content"}`
- **THEN** the system extracts the output text (concatenating `output` and `stdout` fields), and sets `exit_code: 0` as default (since exit code is not present in JSON format)

#### Scenario: Duplicate tool output (format 3)
- **WHEN** the tool response content is `[Duplicate tool output — same content as a more recent call]`
- **THEN** the system marks `exit_code: -1` and `output: "[duplicate]"` and logs an INFO message

#### Scenario: Missing tool response
- **WHEN** no tool response message exists for a given `tool_call_id`
- **THEN** the system marks `exit_code: null` and `output: null` and logs a WARNING

### Requirement: Truncate command output in snapshot
The system SHALL truncate command output to a maximum of 500 characters in the snapshot to keep the JSON file manageable. The system SHALL append `"… (truncated)"` when output exceeds the limit.

#### Scenario: Short output stored in full
- **WHEN** command output is 300 characters
- **THEN** the system stores all 300 characters without truncation marker

#### Scenario: Long output truncated
- **WHEN** command output is 2000 characters
- **THEN** the system stores the first 497 characters followed by `"… (truncated)"`

### Requirement: Include shell commands in global insights
The system SHALL compute global aggregate statistics for shell commands across all sessions.

#### Scenario: Global command counts computed
- **WHEN** 116 sessions contain a total of 500 shell commands, 12 of which have non-zero exit codes
- **THEN** `global_insights.commands.total_commands` SHALL be 500, and `global_insights.commands.failed_commands` SHALL be 12

#### Scenario: Most executed commands ranked
- **WHEN** the most frequently run command is `git status` (45 times)
- **THEN** `global_insights.commands.most_executed_commands[0]` SHALL have `command: "git status"` and `count: 45`

#### Scenario: Failed commands listed
- **WHEN** `npm install` fails with exit code 1 in 3 sessions
- **THEN** `global_insights.commands.failed_commands_list` SHALL include an entry with `command: "npm install"` and `failure_count: 3`

### Requirement: Shell command data schema in snapshot
Each session in the snapshot SHALL contain a `shell_commands` array where each entry follows the schema: `command` (string), `tool_name` (string), `exit_code` (int or null), `output` (string or null, truncated to 500 chars), `success` (boolean: true if exit_code == 0), `timestamp` (ISO datetime string), `message_id` (int), and `tool_call_id` (string).

#### Scenario: Successful command entry
- **WHEN** a `git status` command exits with code 0 and produces output "On branch main\nnothing to commit"
- **THEN** the snapshot entry SHALL have `success: true`, `exit_code: 0`, `output: "On branch main\nnothing to commit"`

#### Scenario: Failed command entry
- **WHEN** an `npm install` command exits with code 1 and produces error output
- **THEN** the snapshot entry SHALL have `success: false`, `exit_code: 1`