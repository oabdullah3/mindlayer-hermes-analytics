## Context

Hermes Analytics currently has a Flask REST API (`server.py`, port 5555) that serves snapshot data as structured JSON. The snapshot contains sessions with embedded skills, tools, shell commands, user messages, and error data, plus pre-computed global insights. There is no UI — users must query raw API endpoints or inspect `snapshot_latest.json` directly.

We're building a Streamlit dashboard that reads from the existing API. Streamlit is chosen because:
- Python-native (same language as the rest of the project)
- Zero frontend build step — pure Python
- Built-in support for tables, charts, metrics, and sidebar navigation
- Plotly integration for rich interactive charts
- Single command to run: `streamlit run dashboard.py`

**Constraints:**
- No changes to `server.py`, `collector.py`, or the snapshot schema
- Dashboard reads data via HTTP from the Flask API (not direct filesystem reads), so it works in both local and remote server modes
- Must handle gracefully when the API is unavailable or the snapshot is empty
- Must work with whatever data exists in the snapshot — no hardcoded assumptions about session count, tool names, or skill names

## Goals / Non-Goals

**Goals:**
- Create a single `dashboard.py` entry point with multi-page navigation
- Build four focused dashboard pages: session overview, session detail, skills analytics, tools analytics
- Build a portal/home page that unifies navigation and shows cross-domain summary metrics
- All pages read from a single `/api/snapshots/latest` call at app startup (shared session state)
- Use Plotly for charts (bar charts, histograms, timelines)
- Graceful empty/error states on every page
- Add `streamlit` and `plotly` to `requirements.txt`

**Non-Goals:**
- Real-time streaming or auto-refresh — manual browser refresh to reload
- Authentication or multi-user support in the dashboard
- Custom CSS/styling beyond Streamlit defaults
- Export to CSV/PDF in this change
- Modifying the REST API or adding new endpoints

## Decisions

### Decision 1: Single `dashboard.py` with Streamlit native multi-page navigation

**Chosen:** A single `dashboard.py` file using `st.navigation` with `st.Page` objects for each dashboard page. All pages share the same `st.session_state` for the loaded snapshot data.

**Rationale:** Streamlit's native multi-page support (`st.navigation` / `st.Page`) gives us sidebar navigation without the complexity of a custom router. A single file keeps the codebase simple and avoids the `pages/` directory convention which can lead to import issues. All pages share `st.session_state.snapshot` for zero-redundancy data loading.

**Alternatives considered:**
- Separate files in `pages/` directory — rejected; harder to share state, implicit routing
- Custom HTML/CSS navigation — rejected; over-engineered for 5 pages

### Decision 2: Single API call at startup, cached in session state

**Chosen:** On first load, fetch `GET /api/snapshots/latest` once and store the result in `st.session_state.snapshot`. Every page reads from this cached snapshot. No per-page API calls.

**Rationale:** The snapshot is the single source of truth. Fetching it once avoids redundant network calls and ensures all pages show consistent data. The snapshot is a batch artifact — there's no benefit to partial fetches.

**Alternatives considered:**
- Per-page API calls to individual endpoints (`/api/sessions`, `/api/skills`, etc.) — rejected; adds latency, unnecessary since the full snapshot is needed for cross-domain metrics on the portal page
- Direct filesystem read of `snapshot_latest.json` — rejected; breaks remote mode (dashboard on different machine than collector)

### Decision 3: Plotly for charts, Streamlit native for tables

**Chosen:** Use Plotly (`plotly.express` and `plotly.graph_objects`) for all visualizations (bar charts, histograms, timelines, pie charts). Use `st.dataframe` and `st.metric` for tabular data and summary cards.

**Rationale:** Plotly provides interactive charts (hover tooltips, zoom, pan) out of the box. Streamlit's native charting (`st.bar_chart`, `st.line_chart`) is limited — no tooltips, no multi-series grouping. Plotly integrates seamlessly with Streamlit via `st.plotly_chart`. Tables benefit from Streamlit's built-in `st.dataframe` with sorting and column configuration.

### Decision 4: Portal page as the home/landing page

**Chosen:** The `dashboard-portal` spec defines a landing page that shows cross-domain summary cards (total sessions, total skill loads, total tool calls, top skills, top tools) drawn from the snapshot. The sidebar navigation lists all pages. The portal page is the default route.

**Rationale:** A landing page gives users immediate value — they see key numbers before drilling into specific dashboards. It also serves as the navigation hub if sidebar is collapsed.

### Decision 5: API base URL configurable via environment variable

**Chosen:** The dashboard reads `API_BASE_URL` from environment, defaulting to `http://localhost:5555`. This allows the dashboard to connect to a remote server instance.

**Rationale:** The server may run on a different machine in production (remote collector mode). Hardcoding `localhost` would break this. An env var is the simplest configuration mechanism — no config file needed.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Snapshot grows large (500KB+), slows page load | Single load at startup; subsequent page navigations are instant (data already in memory) |
| New data fields in snapshot not reflected in dashboard | Dashboards render whatever fields they understand; unknown fields are ignored. Follow-up change can add new visualizations |
| Streamlit server crashes or hangs | Standard Streamlit error boundaries; no data loss since snapshot is read-only |
| Plotly charts may be slow with thousands of data points | Paginate large tables (st.dataframe handles this natively); aggregate charts at reasonable granularity |

## Open Questions

1. Should we add a "Refresh Data" button that re-fetches the snapshot without restarting the dashboard?
2. Should charts have a dark mode toggle, or follow Streamlit's theme setting?
