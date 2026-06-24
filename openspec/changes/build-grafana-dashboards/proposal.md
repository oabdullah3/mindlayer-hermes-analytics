## Why

The REST API serves data, but dashboards need visual panels — bar gauges, time series, tables, heatmaps — to make skill and tool usage patterns visible at a glance. Grafana is the industry-standard telemetry frontend, and provisioning dashboards as code (JSON files) means zero manual setup: clone the repo, run one script, and all dashboards appear with no UI clicking.

## What Changes

- New `grafana/provisioning/` directory with datasource YAML configs and dashboard JSON files
- **2 datasource configs:**
  - `sqlite-datasource.yaml` — local mode, queries `~/.hermes/state.db` directly via `frser-sqlite-datasource` plugin
  - `infinity-datasource.yaml` — remote mode, queries the REST API (`/api/skills`, `/api/tools`, etc.) via `yesoreyeram-infinity-datasource` plugin
- **4 provisioned dashboards (⭐ = primary USP):**
  - `skills-analytics.json` ⭐ — skill load leaderboard, timeline, token cost table, histogram, weekly trend, auto-vs-manual pie
  - `tools-analytics.json` ⭐ — tool call leaderboard, timeline, duration table, errors stat, co-occurrence heatmap, terminal breakdown
  - `session-overview.json` — session stats, token/cost time series, session table, platform pie, model bar gauge
  - `session-detail.json` — drill-down dashboard with session header, token breakdown, skills loaded table, tool calls bar chart, user messages, errors panel
- Dashboards use Grafana dashboard linking (click session row → drill into session detail)
- All dashboards include time range picker support and Grafana templating variables

## Capabilities

### New Capabilities

- `skills-dashboard`: Bar gauge leaderboard, time series timeline, token cost table, load histogram, weekly trend, auto-vs-manual pie chart for skill usage analytics
- `tools-dashboard`: Bar gauge leaderboard, time series timeline, duration table, error stat, co-occurrence heatmap, terminal breakdown for tool usage analytics
- `session-overview-dashboard`: Stat panels, token/cost time series, session table with dashboard linking, platform pie, model bar gauge
- `session-detail-dashboard`: Drill-down session view with header, token breakdown, skills loaded, tool calls bar chart, user messages table, errors log panel
- `grafana-datasources`: SQLite and Infinity/JSON datasource provisioning for local and remote modes

### Modified Capabilities

None — this is a greenfield project with no existing specs.

## Impact

- **New directory:** `grafana/provisioning/dashboards/` with 4 JSON files
- **New directory:** `grafana/provisioning/datasources/` with 2 YAML files
- **Dependencies:** Grafana OSS v13+, `frser-sqlite-datasource` plugin, `yesoreyeram-infinity-datasource` plugin
- **Datasource targets:** SQLite reads `~/.hermes/state.db` directly; Infinity queries REST API at `http://localhost:5555/api/`
- **No server code changes** — dashboards consume the existing REST API contract
