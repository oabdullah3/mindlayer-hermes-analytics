## Why

The Streamlit dashboards (build-streamlit-dashboards) were implemented as a functional first pass, but suffer from three categories of issues: (1) **data gaps** — session titles and tool names are missing because the collector isn't reading them from available sources, (2) **visual bugs** — truncated KPI cards, overlapping legends, zero-spacing bar charts, broken pie chart legends, and (3) **UX gaps** — checkbox-based single selection, bare session IDs instead of human-readable names, abrupt text truncation without indicators. This overhaul makes the dashboards production-ready by fixing at both the collector (data) and dashboard (presentation) layers.

## What Changes

- **Collector: extract session `title`** from `state.db` — the column exists and is populated for 88% of sessions but is hardcoded to `None`
- **Collector: resolve tool names from `tool_calls` JSON** — `messages.tool_name` is NULL for 72% of tool messages; instead, parse the `tool_calls` JSON column in the preceding assistant message to get correct `function.name` values, and count them per session
- **Dashboard: KPI card truncation fix** — ensure all metric cards render fully without cut-off
- **Dashboard: chart spacing** — add spacing between histogram bars (bargap)
- **Dashboard: pie chart overhaul** — remove the broken sidebar legend; use hover tooltips with name/count/percentage; generate colors with the Golden Ratio algorithm for visual distinction
- **Dashboard: legend overlap fix** — position legends below or beside charts to avoid overlapping with toolbar controls
- **Dashboard: single-row selection** — replace checkboxes with radio buttons in the session table
- **Dashboard: session display names** — show `chat_name` (title) alongside session ID in dropdowns, tables, and detail headers
- **Dashboard: message truncation** — add "… (truncated)" suffix and styled containers for user messages
- **Dashboard: tool calls table** — show tool name + count + result status; remove the redundant message_ids column
- **Dashboard: drill-down context** — show session title in skill and tool drill-down results

## Capabilities

### New Capabilities

- `visual-overhaul`: All dashboard visual and data-quality fixes described above

### Modified Capabilities

- `data-extraction`: Collector must extract `title` from sessions and resolve tool names from `tool_calls` JSON instead of relying on NULL `tool_name` column

## Impact

- **Collector**: `userend/collector.py` — modify session extraction to include `title`, rewrite tool aggregation to use `tool_calls` JSON
- **Dashboard**: `dashboard.py` — visual fixes, spacing, legends, pie chart, radio buttons, session name display, message truncation indicators
- **Snapshot schema**: adds `chat_name` (previously always None) populated from `sessions.title`; tool names become accurate
- **No breaking changes** to the REST API or snapshot wire format — only new/improved field values
