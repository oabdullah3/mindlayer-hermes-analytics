## Why

Hermes Analytics currently has no visualization layer. The REST API (`server.py`) serves raw JSON endpoints, and the snapshot (`snapshot_latest.json`) contains rich session, skill, and tool data, but there is no way to browse, explore, or derive insights from this data without manually querying API endpoints or inspecting JSON. The archived `build-grafana-dashboards` change was never implemented. We need a lightweight, Python-native dashboard solution that reads from the existing API and presents the data in discoverable, interactive pages.

## What Changes

- Create a Streamlit dashboard application (`dashboard.py`) that reads from the existing Flask REST API
- Build four focused dashboard pages, each covering one data domain: sessions overview, session detail, skills analytics, tools analytics
- Build a portal/dashboard hub page with sidebar navigation that unifies all pages into one cohesive application
- Add `streamlit` and `plotly` to `requirements.txt`
- Each dashboard page renders gracefully with an empty-state when no data is available

## Capabilities

### New Capabilities
- `session-overview-dashboard`: Overview page listing all sessions with key metrics (model, platform, duration, token count, skill count, tool call count), aggregate summary cards, and filtering/sorting
- `session-detail-dashboard`: Drill-down page for a single session showing all metrics broken down (skills loaded, tool calls, shell commands, user messages, errors, tokens, platform info) with inline visualizations
- `skills-dashboard`: Skills usage analytics across all sessions — ranking table by load count, token estimate distribution, most common preceding user messages, usage timeline
- `tools-dashboard`: Tool call analytics across all sessions — ranking table by call count, tool call distribution, session-tool correlation, usage timeline
- `dashboard-portal`: Unifying portal page with sidebar navigation, shared data loading layer (single API call to `/api/snapshots/latest`), consistent layout/styling across all pages, and a landing/home page showing cross-domain summary

### Modified Capabilities
<!-- None — all dashboard pages are new capabilities built on the existing API -->

## Impact

- Affected code: New file `dashboard.py` (~400-600 lines)
- Affected dependencies: `requirements.txt` gains `streamlit` and `plotly`
- No changes to `collector.py`, `server.py`, or snapshot schema
- Dashboard reads from existing REST API endpoints — no new API endpoints required
