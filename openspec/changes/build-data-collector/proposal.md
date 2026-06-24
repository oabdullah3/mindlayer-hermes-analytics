## Why

Hermes Agent produces rich usage data across SQLite, JSONL logs, and log payloads, but this data is raw and unaggregated. Without a collector, there is no way to extract, enrich, and expose skill/tool analytics in a structured format consumable by a dashboard. This is the foundation layer — every downstream component (API, Grafana dashboards) depends on it.

## What Changes

- New `collector.py` script that reads Hermes data sources and produces a structured snapshot JSON
- Reads from 5 data sources: `~/.hermes/state.db`, `~/.hermes/sessions/*.jsonl`, `~/.hermes/logs/agent.log`, `~/.hermes/log_payloads/`, `~/.hermes/.skills_prompt_snapshot.json`
- Executes 7 extraction steps: session list, skill load detection, preceding user messages, tool call aggregation, token estimation, session user messages, error parsing
- Produces `snapshot_latest.json` with sessions, skill loads, tool calls, user messages, errors, and global insights
- Supports two modes: local file write (default) and remote push via `HERMES_ANALYTICS_REMOTE` env var
- Runs manually, via cron, or triggered by the REST API `/api/refresh` endpoint

## Capabilities

### New Capabilities

- `data-extraction`: Query state.db and parse JSONL/log files to extract structured session, skill, tool, and error data from Hermes Agent's raw output
- `snapshot-generation`: Assemble extracted data into a versioned JSON snapshot schema consumable by the REST API and downstream consumers
- `remote-push`: Optionally POST the generated snapshot to a remote API server for multi-user/team dashboard scenarios

### Modified Capabilities

None — this is a greenfield project with no existing specs.

## Impact

- **New file:** `collector.py` (~300-400 lines)
- **New file:** `snapshot_latest.json` (generated artifact, gitignored)
- **Dependencies:** Python stdlib (`sqlite3`, `json`, `os`, `glob`, `subprocess`), `requests` (for remote push mode)
- **Data sources read:** `~/.hermes/state.db`, `~/.hermes/sessions/`, `~/.hermes/logs/agent.log`, `~/.hermes/log_payloads/`, `~/.hermes/.skills_prompt_snapshot.json`
- **Env vars:** `HERMES_HOME` (optional, defaults to `~/.hermes`), `HERMES_ANALYTICS_REMOTE` (optional, enables push mode)
- **No modifications to Hermes core** — purely external consumer
