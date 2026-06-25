## 1. Collector — Session Title Extraction

- [x] 1.1 Replace `session["chat_name"] = None` with `session.pop("title", None)` in `assemble_snapshot()`
- [x] 1.2 Include `title` in the session fields whitelist (add to the `if key not in (...)` check)

## 2. Collector — Tool Name Resolution via tool_calls JSON

- [x] 2.1 Write `_parse_tool_calls_json(content)` helper: parse JSON string, iterate array, extract `function.name` for each entry, return list of names
- [x] 2.2 Rewrite `aggregate_tool_calls()`: instead of `GROUP BY tool_name WHERE role='tool'`, query all assistant messages with non-null `tool_calls`, extract names per message, count by positionally matching tool-response rows
- [x] 2.3 Add fallback behavior: if `tool_calls` is null/malformed for all messages, fall back to the old `messages.tool_name` column query
- [x] 2.4 Add success rate computation: for each tool name, compute `successes / total_calls` from tool responses with exit code 0 or non-empty output
- [x] 2.5 Run collector and verify tool names are resolved (no more "unknown" entries)

## 3. Dashboard — Visual Bug Fixes

- [x] 3.1 Fix KPI card truncation on portal home page (wrap in columns with appropriate width, or use `st.columns` with proportional widths)
- [x] 3.2 Fix session detail header metric truncation (model names, dates)
- [x] 3.3 Add `bargap=0.15` to all `px.histogram` calls (token estimate histogram, tool calls per session histogram)
- [x] 3.4 Add `bargap=0.15` to all `px.bar` calls for consistency
- [x] 3.5 Reposition all legend-bearing charts: move legends from `y=1.02` (above) to `y=-0.3` (below) with `orientation="h"`

## 4. Dashboard — Pie Chart Overhaul

- [x] 4.1 Implement `golden_ratio_colors(n)` function: generate N HSL colors using Golden Ratio conjugate (0.618) for hue rotation
- [x] 4.2 Apply Golden Ratio colors to `px.pie` call in tools page
- [x] 4.3 Remove legend from pie chart; ensure hover tooltips show tool name, call count, and percentage
- [x] 4.4 Set `hole=0.4` (keep existing donut style)

## 5. Dashboard — UX Improvements

- [x] 5.1 Session table: add "Title" column showing `chat_name` (or "Untitled" when NULL)
- [x] 5.2 Session detail dropdown: display `"{chat_name or 'Untitled'} — {session_id[:20]}"` as option label
- [x] 5.3 Session detail header: show chat_name as primary heading if available
- [x] 5.4 Replace message dump with styled containers: `st.container(border=True)` with timestamp header
- [x] 5.5 Add "… (truncated)" suffix to truncated user messages (content > 300 chars)
- [x] 5.6 Tool calls table: replace columns with Tool Name, Call Count, Success Rate; remove message_ids column

## 6. Dashboard — Drill-Down Context

- [x] 6.1 Skill drill-down: add "Session Title" column to results table
- [x] 6.2 Tool drill-down: add "Session Title" column to results table

## 7. Dashboard — Tools Chart Improvements

- [x] 7.1 Add "Show all tools" checkbox for the tools bar chart, defaulting to top 10
- [x] 7.2 Ensure long tool names (40+ chars) don't overlap modebar — increase left margin or truncate labels with ellipsis

## 8. Verification

- [ ] 8.1 Re-run collector: verify `chat_name` is populated, `tool_calls` has correct names, no "unknown" tools
- [ ] 8.2 Launch dashboard and visually verify all 5 pages: no truncation, bar gaps, legend positions, pie colors, dropdown labels, message containers
- [ ] 8.3 Run full test suite (42 tests) — update test expectations if collector output changed
