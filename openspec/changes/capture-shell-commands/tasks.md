## 1. Shell command extraction function

- [x] 1.1 Create `extract_shell_commands(conn, session_id) -> list[dict]` that queries assistant messages with `tool_calls IS NOT NULL`, parses the JSON, and collects all tool calls whose `function.arguments` contain a `command` key
- [x] 1.2 For each extracted command, fetch the matching tool response row from `messages` where `role='tool' AND tool_call_id = ? AND session_id = ?`
- [x] 1.3 Build the shell command entry dict: `command`, `tool_name`, `exit_code`, `output`, `success`, `timestamp`, `message_id`, `tool_call_id`
- [x] 1.4 Handle malformed `tool_calls` JSON gracefully — log WARNING and skip that message's commands

## 2. Response parsing (exit code + output)

- [x] 2.1 Implement JSON response parser: extract `output` and `stdout` fields, concatenate, default `exit_code=0`
- [x] 2.2 Implement bracketed-text parser: regex match `[terminal] ran \`...\` -> exit N, ...` to extract exit code and use full content as output
- [x] 2.3 Handle duplicate placeholder `[Duplicate tool output — ...]`: set `exit_code=-1`, `output="[duplicate]"`, log INFO
- [x] 2.4 Handle missing tool response: set `exit_code=null`, `output=null`, log WARNING
- [x] 2.5 Handle empty content in tool response: log WARNING, set `exit_code=null`, `output=null`

## 3. Output truncation

- [x] 3.1 Truncate command output to 500 characters with `"… (truncated)"` suffix when output exceeds the limit
- [x] 3.2 Preserve full output when 500 chars or fewer — no truncation marker

## 4. Integration into per-session pipeline

- [x] 4.1 Call `extract_shell_commands()` in `collect()` after step 4 (tool aggregation) for each session
- [x] 4.2 Add `shell_commands` to the session schema dict alongside `skills_loaded`, `tool_calls`, `user_messages`, `errors`
- [x] 4.3 Include `shell_commands` in the allowlist of session keys during cleanup (the `for key in list(session.keys())` block)

## 5. Global insights enrichment

- [x] 5.1 Add command aggregation in `compute_global_insights()`: tally `total_commands` and `failed_commands` across all sessions
- [x] 5.2 Build `most_executed_commands` list (top 20 by frequency, each with `command` string and `count`)
- [x] 5.3 Build `failed_commands_list` (commands with non-zero exit codes, each with `command` string and `failure_count`, sorted by failure_count DESC)
- [x] 5.4 Add the `commands` sub-object to the global_insights return dict

## 6. Verification

- [x] 6.1 Run `python3 collector.py` against real `~/.hermes/` data and verify shell_commands appear in `snapshot_latest.json` for sessions with terminal tool usage
- [x] 6.2 Verify exit codes are correctly parsed from both JSON and bracketed-text response formats
- [x] 6.3 Verify `global_insights.commands` contains `total_commands`, `failed_commands`, `most_executed_commands`, and `failed_commands_list`
- [x] 6.4 Verify no regressions: session count, skill loads, and tool counts remain unchanged (116/153/208 baseline)
