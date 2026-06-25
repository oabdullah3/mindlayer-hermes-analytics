## Why

The current Hermes Analytics workflow requires running a bash script (`hermes-snapshot`) outside Hermes and a separate `install.sh` config wizard. Users can't trigger analytics from within a Hermes chat session. The project also isn't structured as a proper Hermes plugin, meaning it can't leverage the plugin system's lifecycle hooks, slash command registration, or skill bundling. This change makes Hermes Analytics a first-class Hermes plugin so users get `/hermes-snapshot-analytics` right in their chat sessions.

## What Changes

- **BREAKING**: Remove `userend/install.sh` config wizard — configuration moves to environment variables with hardcoded defaults
- **BREAKING**: Remove the standalone `hermes-snapshot` bash script — replaced by the Hermes plugin slash command
- Add Hermes plugin structure (`plugin.yaml`, `__init__.py` with `register()`) to `userend/`
- Register a single slash command `/hermes-snapshot-analytics` that orchestrates: start local server → collect snapshot → start local dashboard → show URL
- Snapshot always POSTs to both local server (if running) and remote server (if configured via env), falling back to local file save
- Local dashboard has a "Shutdown" button that kills the spawned server + Streamlit processes
- Reorganize into `userend/` (plugin + local single-user dashboard) and `remoteend/` (remote Flask server + multi-user dashboard with user filters)
- Remote server URL is hardcoded in production code, overridable via `HERMES_ANALYTICS_REMOTE` env var
- The collector resolves username from Hermes' own context (no separate config file needed)

## Capabilities

### New Capabilities
- `hermes-plugin-registration`: Register Hermes Analytics as a Hermes plugin with `plugin.yaml`, `__init__.py`, `register(ctx)`, registering the `/hermes-snapshot-analytics` slash command
- `slash-command-orchestration`: The slash command handler that starts local Flask server, runs collector (push to local + remote), starts Streamlit dashboard, and returns dashboard URL to chat
- `dashboard-shutdown`: Local dashboard includes a "Shutdown" button in the Streamlit sidebar that kills both the Flask server and Streamlit process
- `remoteend-multi-user`: Remote server + multi-user dashboard in `remoteend/` with user filters, user leaderboard, and per-user metrics

### Modified Capabilities
- `user-config-setup`: **BREAKING** — Replace `~/.hermes-analytics.conf` file-based config with environment variables. Remote URL is hardcoded with env var override. Username resolved from Hermes context.
- `remote-push`: Collector always attempts POST to both local and remote servers. Fallback order: local server → remote server → local file save.
- `userend-client-structure`: Restructure `userend/` from standalone scripts + collector to a Hermes plugin package with dashboards bundled alongside.

## Impact

- `userend/install.sh` — removed
- `userend/hermes-snapshot` — removed
- `userend/collector.py` — refactored to work as plugin module (no standalone `main()`)
- `userend/` — gains `plugin.yaml`, `__init__.py`, dashboard code
- `server.py` at root — split: local variant stays in `userend/`, remote multi-user variant moves to `remoteend/`
- `dashboard.py` at root — split: local single-user dashboard in `userend/`, multi-user dashboard in `remoteend/`
- `remoteend/` — new directory for remote server + multi-user dashboard
- Root `install.sh`, `collector.py`, `server.py`, `dashboard.py` — may be simplified or become shims
- `~/.hermes-analytics.conf` — no longer created or read; users set `HERMES_ANALYTICS_REMOTE` env var
