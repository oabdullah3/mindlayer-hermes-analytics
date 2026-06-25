## Why

Hermes Analytics currently captures session-level metadata (skills, tools, shell commands, tokens) but completely ignores `~/.hermes/log_payloads/` — a rich directory of structured JSON audit logs from the `mindlayer-confluence-cli` tool. These 66 payloads across 5 days contain per-command telemetry (duration, operation type, search queries, page IDs, workflow stages) that reveals how Confluence is actually being used through Hermes. A dedicated collector step and dashboard unlock operational insights currently invisible.

## What Changes

- **New collector step** (Step 9): reads all `~/.hermes/log_payloads/YYYY-MM-DD/*.json` files, parses their common schema, and aggregates command-level statistics
- **New snapshot fields**: `log_payloads` section in `snapshot_latest.json` with per-command records and global aggregates (operation type breakdown, duration stats, top pages, top search queries, workflow pipeline tracking)
- **New Streamlit dashboard page**: "Confluence Audit" dashboard with operation leaderboard, duration distribution, page interaction heatmap, workflow pipeline Sankey/bar (prepare → show-changes → finalize), daily usage timeline, and search query frequency table
- **requirements.txt update**: add `streamlit` and `plotly` (already planned for the Streamlit dashboard change)

## Capabilities

### New Capabilities

- `log-payloads-extraction`: Parse and aggregate structured JSON payloads from `~/.hermes/log_payloads/`, extracting per-command telemetry (tool_name, command, user_email, duration_ms, status, input_flags, result summary, workflow stage) into the snapshot
- `confluence-audit-dashboard`: Streamlit page visualizing Confluence CLI operations — operation distribution, duration statistics, page interaction leaderboard, search query analytics, workflow pipeline completion rates, and daily usage timeline

### Modified Capabilities

None — this is a greenfield addition. No existing specs change.

## Impact

- **New file:** `dashboard.py` (Streamlit app with Confluence Audit page, plus Skills/Tools/Sessions pages from the overarching Streamlit migration)
- **Modified file:** `collector.py` — adds Step 9 `extract_log_payloads()` and integrates output into snapshot generation
- **Modified file:** `requirements.txt` — adds `streamlit` and `plotly`
- **Modified file:** `snapshot_latest.json` schema — new `log_payloads` top-level field alongside `sessions` and `global_insights`
- **Data source:** `~/.hermes/log_payloads/**/*.json` (66 files, ~5 days of history)
- **No server.py changes** — the dashboard reads snapshot directly or via existing REST API
