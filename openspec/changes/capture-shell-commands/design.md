## Context

The collector (`collector.py`) already has a 7-step pipeline that extracts sessions, skill loads, tool calls (aggregated by name), user messages, and global insights into `snapshot_latest.json`. The current `aggregate_tool_calls()` function (step 4) queries only the `messages` table's `role='tool'` rows, grouping by `tool_name` to produce counts. It does not parse assistant-side `tool_calls` JSON or join with tool responses for detail.

The Hermes `state.db` stores all data needed:
- **Assistant messages**: `tool_calls` JSON with `function.name` and `function.arguments` (contains `command` string)
- **Tool response messages**: `content` field with three formats — bracketed text `[terminal] ran \`CMD\` -> exit N, ...`, JSON `{"output": "..."}`, or duplicate marker

This design adds an eighth extraction step that operates per-session, correlating assistant tool calls with their responses.

## Goals / Non-Goals

**Goals:**
- Extract every command executed via `terminal` (or any tool with `command` in arguments) across all sessions
- Capture exit code, truncated output, success/failure, and timestamp for each command
- Surface command-level data in global insights (totals, failures, most-run)

**Non-Goals:**
- Full (untruncated) command output storage — snapshot size is a concern
- Cross-session command deduplication at the snapshot level
- Replaying or re-executing commands
- Changing the existing `tool_calls` aggregation — we extend it alongside, not replace it

## Decisions

### 1. New extraction function vs. modifying `aggregate_tool_calls()`
**Decision**: Create a new `extract_shell_commands()` function that runs independently alongside `aggregate_tool_calls()`.
**Why**: The aggregation function groups by `tool_name` from response rows; shell extraction joins assistant-side JSON with responses by `tool_call_id`. These are different queries with different schemas. Keeping them separate avoids breaking the existing tool aggregation and allows each to evolve independently.
**Alternative considered**: Extending `aggregate_tool_calls()` to optionally include commands. Rejected because it would require a union-type return schema that complicates downstream consumers.

### 2. How to identify "execute" tool calls
**Decision**: Scan assistant messages where `tool_calls` JSON contains an object with `function.arguments` that has a `command` key. Match by `tool_call_id` with tool response rows.
**Why**: Tool names vary (`terminal`, potentially `bash`, `shell`, etc.) depending on which MCP servers or adapters are configured. The `command` key is the universal signal. The `tool_call_id` in the assistant JSON matches `messages.tool_call_id` in the response table.
**Alternative considered**: Hardcoding a list like `["terminal", "bash"]`. Rejected — not extensible for future tool names.

### 3. Response parsing strategy
**Decision**: Three-tier parser — try JSON first (`{"output": "...", "stdout": "..."}`), then bracketed text regex (`[terminal] ran \`...\` -> exit N, ...`), then duplicate marker.
**Why**: Mirrors the successful pattern already used in `_parse_skill_name()`. JSON responses lack explicit exit codes — default to 0. Duplicate markers are unparseable → exit code -1.
**Alternative considered**: Only parse one format. Rejected because real Hermes data shows all three formats in the wild.

### 4. Output truncation
**Decision**: Truncate at 500 characters with `"… (truncated)"` marker. Same approach as `extract_user_messages()`.
**Why**: Consistency, and avoids snapshot bloat. 500 chars gives enough output for context (error messages, first part of long listings).

### 5. Global insights enrichment
**Decision**: Add a `commands` sub-object under `global_insights` with `total_commands`, `failed_commands`, `most_executed_commands` (top 20), and `failed_commands_list`.
**Why**: Enables the future Grafana dashboards to show "most executed commands" and "highest failure rate commands" without per-session aggregation in the viewer.

## Risks / Trade-offs

- **[Risk] Snapshot size increases**: Each command entry is ~700 bytes (command + truncated output). With ~500 commands, that's ~350KB addition to the snapshot. → **Mitigation**: Output truncation (500 chars). JSON compression is adequate.
- **[Risk] Missing tool responses**: Some tool calls may have no matching response row (Hermes crash, etc.). → **Mitigation**: Log a WARNING, store `exit_code: null, output: null`. Don't lose the command itself.
- **[Risk] Parsing ambiguity**: The `[terminal] ran \`...\` -> exit N` format could vary. → **Mitigation**: Use a lenient regex with fallback to `exit_code: null` if the pattern doesn't match.

## Open Questions

- Should we also capture the `cwd` directory if present in the tool arguments? (Some Hermes tool calls include `cwd` alongside `command`.) → Worth including if available, as a discretionary field.
