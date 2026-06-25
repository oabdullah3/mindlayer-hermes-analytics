## Context

The `build-streamlit-dashboards` change delivered a functional 5-page Streamlit dashboard reading from the REST API. User feedback and stress-testing with real data (117 sessions, 116 distinct tool names, 25 distinct skills) surfaced visual bugs, UX issues, and two data gaps at the collector level.

**Current state:**
- Collector hardcodes `chat_name = None` despite `sessions.title` being populated for 103/117 sessions (88%)
- Collector reads `messages.tool_name` which is NULL for 1517/2116 tool messages (72%); correct names exist in the `tool_calls` JSON column of the preceding assistant message
- Dashboard renders but has overlapping legends, zero-spacing bar charts, truncated KPI cards, abrupt message truncation, and bare session IDs

**Constraints:**
- No changes to the REST API or snapshot wire format
- No new Python dependencies
- Must remain a single `dashboard.py` file

## Goals / Non-Goals

**Goals:**
- Surface `sessions.title` as `chat_name` in the snapshot, enabling human-readable session identification across all dashboard pages
- Rewrite tool aggregation to resolve names from `tool_calls` JSON, eliminating ~74 "unknown" tool entries
- Fix all chart visual bugs: overlapping legends, zero-spacing histogram bars, broken pie chart legend, truncated KPI cards
- Improve UX: radio-button session selection, message truncation indicators, session titles in drill-downs
- Generate visually distinct colors for multi-category charts using the Golden Ratio algorithm

**Non-Goals:**
- Redesign the dashboard layout or page structure
- Add new dashboard pages
- Change the snapshot JSON schema (only populate existing fields correctly)
- Fix `skill_name = "unknown"` (5 cases) — those are genuine Hermes-level data gaps (empty content, "Skill name is required" errors)

## Decisions

### D1: Tool name resolution via `tool_calls` JSON
**Choice:** Parse the `tool_calls` JSON column in assistant messages (role='assistant'), extract `function.name` for each tool call object, then match tool responses (role='tool') by position: the Nth tool response after an assistant message corresponds to the Nth entry in its `tool_calls` array.

**Rationale:** `messages.tool_name` is NULL for 72% of rows — unreliable. The `tool_calls` JSON always contains the correct name. Agent tool calls can be batched (1–N per assistant message), and each generates one tool response row immediately after. Positional matching is deterministic.

**Alternative considered:** Cross-referencing `tool_call_id` with `messages.tool_call_id`. Rejected because `messages.tool_call_id` is equally sparse in the schema.

**Query approach:**
1. Fetch all assistant messages with non-null `tool_calls` for a session
2. For each, extract `function.name` per tool call in the JSON array
3. Fetch the next N tool-response rows (role='tool') that follow each assistant message
4. Count tool names for aggregation

### D2: Session title field
**Choice:** Read `sessions.title` and map it to `chat_name` in the snapshot. Keep the existing key name `chat_name` (no schema change).

**Rationale:** The column exists and is populated. One-line change: replace `session["chat_name"] = None` with `session["chat_name"] = session.pop("title", None)`. The `title` column is already fetched by `SELECT *`.

### D3: Pie chart legend → hover tooltips
**Choice:** Remove the Plotly sidebar legend from the tools pie chart. Rely on hover tooltips showing tool name, call count, and percentage. For small slices where Plotly doesn't render labels, the hover tooltip still works.

**Rationale:** 116 unique tools makes a sidebar legend unusably tall. Hover tooltips scale infinitely.

### D4: Golden Ratio color generation
**Choice:** Generate N HSL colors using `hue = (i × φ⁻¹) mod 1` where φ⁻¹ ≈ 0.618033988749895 (the golden ratio conjugate). Saturation 70%, lightness 50%.

**Rationale:** This algorithm maximizes perceptual distance between adjacent colors without a fixed palette. Works for any N. Standard approach used in d3.js, Apache ECharts, etc.

### D5: Histogram bar spacing
**Choice:** Set `bargap=0.15` on all `px.histogram` and `px.bar` calls.

### D6: Legend repositioning
**Choice:** Place legends horizontally below charts (`legend=dict(orientation="h", yanchor="top", y=-0.3)`) instead of above (`y=1.02`).

### D7: Session selection UX
**Choice:** Use `st.dataframe` with `selection_mode="single-row"` (already in place). The checkboxes the user sees are actually single-select radio behavior — clarify by adding a visual indicator. If Streamlit's native rendering shows checkboxes even in single mode, add a helper column with radio button indicators.

### D8: Message display styling
**Choice:** Add "… (truncated)" suffix to truncated messages and wrap each message in `st.container(border=True)` with a timestamp header.

### D9: Tool calls table maturity
**Choice:** Show tool name + call count. Remove the message_ids column. Add a "Success Rate" column computed from tool responses (exit code 0 or non-empty output = success). For batch calls, show aggregate count and success rate.

## Risks / Trade-offs

- **[Risk] Tool-call positional matching may miscount if tool responses are interleaved with other messages** → Mitigation: query only tool-role messages directly following each assistant message; if the pattern doesn't hold, fall back to the old `tool_name` column behavior
- **[Risk] Golden Ratio colors may produce similar-looking hues for adjacent indices when N is very large** → Acceptable trade-off; hover tooltips provide precise identification
- **[Risk] `sessions.title` is NULL for 14 sessions** → Mitigation: fall back to session ID display when title is None
