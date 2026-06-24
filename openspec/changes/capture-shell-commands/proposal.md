## Why

The collector currently aggregates tool calls by name only (e.g., "terminal: 24 calls"), discarding the actual shell commands executed, their exit codes, and output. This is the richest operational data in Hermes — it captures which CLI commands the agent ran, which succeeded/failed, and what they produced. Without it, the dashboard cannot answer: "What commands did the agent actually execute?" or "Which commands failed most often?".

## What Changes

- **New extraction step** in the collector that captures shell/execute command details from assistant `tool_calls` JSON and matches them with their tool response (exit code, output)
- **New `shell_commands` field** in each session's snapshot entry: a list of objects with `command`, `tool_name`, `exit_code`, `output_truncated` (first 500 chars), `timestamp`, and `success` boolean
- **Modified `aggregate_tool_calls()`** to optionally include a `commands` sub-list for each tool that supports shell execution
- **New `global_insights` fields**: `total_commands`, `failed_commands`, `most_executed_commands` (top 20 with counts), `failed_commands_list` (commands that exited non-zero)
- Robust parsing of three terminal response formats: plain `[terminal] ran \`CMD\` -> exit N, ...`, JSON `{"output": "..."}`, and duplicate placeholders

## Capabilities

### New Capabilities
- `shell-command-extraction`: Extract individual shell/terminal commands from Hermes tool calls, including the exact command string, exit code, truncated output, and success/failure status

### Modified Capabilities
<!-- No existing specs to modify — this is the first delta on top of the collector -->

## Impact

- **`collector.py`**: New extraction function `extract_shell_commands()`, modifications to `aggregate_tool_calls()`, new `global_insights` computations
- **Snapshot schema**: New `shell_commands` array per session, new `global_insights.commands.*` fields
- **Future dashboards**: A new "Shell Commands" panel in the session detail dashboard for command-level visibility
