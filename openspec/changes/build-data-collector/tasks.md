## 1. Foundation

- [x] 1.1 Create `collector.py` with main entry point and argparse CLI (no args needed for default run)
- [x] 1.2 Resolve `hermes_home` from `HERMES_HOME` env var or default to `~/.hermes`
- [x] 1.3 Validate that `state.db` exists at `{hermes_home}/state.db`; exit with error if missing
- [x] 1.4 Open state.db connection with `sqlite3.connect()` in read-only mode

## 2. Session Extraction (Step 1)

- [x] 2.1 Query `SELECT * FROM sessions ORDER BY started_at DESC` from state.db
- [x] 2.2 Map each row to a session dict with all columns: id, source, user_id, model, started_at, ended_at, ended_reason, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens, estimated_cost_usd, message_count, tool_call_count
- [x] 2.3 Handle empty result set gracefully (produce valid snapshot with zero sessions)

## 3. Skill Load Detection (Step 2)

- [x] 3.1 For each session, query assistant messages WHERE `role='assistant' AND tool_calls IS NOT NULL` and `json_extract(tool_calls, '$[0].function.name') IN ('skill_view', 'skill_manage')`
- [x] 3.2 For each match, fetch the linked tool response WHERE `role='tool' AND tool_call_id = <extracted_call_id>`
- [x] 3.3 Parse skill name from tool response `content` JSON; handle malformed JSON gracefully
- [x] 3.4 Record skill_name, load_message_id, load_timestamp, tool_call_id, content_chars, token_estimate per load
- [x] 3.5 Handle orphaned assistant messages (no matching tool response) with warning log

## 4. Preceding User Messages (Step 3)

- [x] 4.1 For each skill load, query `SELECT content FROM messages WHERE id = skill_load_msg_id - 1 AND role='user'`
- [x] 4.2 Handle edge cases: message not found, role not user, or skill load is first message in session
- [x] 4.3 Attach `preceding_user_message` to each skill load entry

## 5. Tool Call Aggregation (Step 4)

- [x] 5.1 Query `SELECT tool_name, COUNT(*) as c, GROUP_CONCAT(id) as msg_ids FROM messages WHERE role='tool' GROUP BY tool_name` per session
- [x] 5.2 Build per-session `tool_calls` list with tool_name, count, message_ids array
- [x] 5.3 Handle sessions with zero tool calls (empty list)

## 6. Token Estimation (Step 5)

- [x] 6.1 For each skill load, compute `token_estimate = CEIL(LENGTH(content) / 4)`
- [x] 6.2 Set `content_chars = LENGTH(content)` for each skill load

## 7. Session User Messages (Step 6)

- [x] 7.1 Query all `role='user'` messages per session with id, content, timestamp
- [x] 7.2 Truncate content to 200 characters for display in snapshot
- [x] 7.3 Handle sessions with no user messages (empty list)

## 8. Error Parsing (Step 7)

- [x] 8.1 Check for `{hermes_home}/logs/agent.log` existence; skip if missing
- [x] 8.2 Parse lines matching `Tool terminal returned error` with regex, extract session_id from bracketed prefix and duration from parens
- [x] 8.3 Associate errors with their session by matching session_id

## 9. Global Insights

- [x] 9.1 Compute `total_sessions`, `total_messages`, `total_skill_loads` across all sessions
- [x] 9.2 Build skills leaderboard: name, load_count, total_chars, token_estimate per skill across all sessions
- [x] 9.3 Build tools leaderboard: name, call_count per tool across all sessions

## 10. Snapshot Output & Remote Push

- [x] 10.1 Assemble final snapshot dict with `generated_at` (ISO 8601 UTC), `hermes_home`, `sessions`, `global_insights`
- [x] 10.2 Write `snapshot_latest.json` to disk with `json.dump(indent=2)`
- [x] 10.3 Check for `HERMES_ANALYTICS_REMOTE` env var; if set, import requests and POST snapshot
- [x] 10.4 Handle remote POST failure: log error, fall back to local file write
- [x] 10.5 Handle missing `requests` library when remote mode is requested: print install instructions, fall back to local
- [x] 10.6 Print summary: session count, skill load count, tool call count, output path or POST URL to stdout
- [x] 10.7 Update README.md: mark collector as ✅ in project status table, ensure collector quick-start section is accurate, verify architecture diagram matches
