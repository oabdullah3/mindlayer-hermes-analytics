## Context

Hermes Analytics currently requires users to run a bash script (`hermes-snapshot`) outside of Hermes. The project has no Hermes plugin structure — it's a collection of standalone Python scripts with a shell-based install wizard. Users want to trigger analytics from within a Hermes chat session via a slash command.

The Hermes plugin system supports registering slash commands, tools, hooks, skills, and CLI commands through a `register(ctx)` function in `__init__.py` with a `plugin.yaml` manifest. This is the standard, documented way to extend Hermes.

## Goals / Non-Goals

**Goals:**
- Register `/hermes-snapshot-analytics` as a Hermes slash command that works in CLI and gateway sessions
- The slash command orchestrates: start local server → collect snapshot → start dashboard → return URL
- Eliminate the `install.sh` config wizard — all configuration via env vars with sensible defaults
- Snapshot always attempts push to local server first, remote server second, local file as fallback
- Local dashboard has a "Shutdown Analytics" button that kills spawned server + Streamlit processes
- Separate `remoteend/` for the multi-user server + dashboard used in team deployments
- The plugin self-contains the collector, local server, and local dashboard code

**Non-Goals:**
- Dockerizing the remote server (future work)
- Real-time streaming of analytics (snapshot-based model remains)
- Modifying Hermes core
- Supporting the old `~/.hermes-analytics.conf` config file (breaking removal)
- Auto-starting analytics on every Hermes session (explicit slash command invocation only)

## Decisions

### D1: Plugin lives in repo's `userend/`, symlinked to `~/.hermes/plugins/`

**Choice:** Keep source in the repo's `userend/` directory. During setup, create a symlink from `~/.hermes/plugins/hermes-analytics` → `userend/`.

**Rationale:** The plugin code is part of the repo for version control. Hermes discovers plugins by scanning `~/.hermes/plugins/`. A symlink bridges the two. This is simpler than copying files or maintaining two copies.

**Alternatives considered:**
- Copy files to `~/.hermes/plugins/` on install — fragile, drift between source and installed copy
- Use pip entry points — overkill for a single-project plugin, adds packaging complexity

### D2: Slash command handler uses `subprocess` for process orchestration

**Choice:** The slash command handler directly uses `subprocess.Popen` to start the Flask server and Streamlit dashboard, writing PIDs to `/tmp/hermes-analytics-{server,dashboard}.pid`. The collector is called via `subprocess.run` for synchronous execution.

**Rationale:** The handler runs in the Hermes process. Starting child processes via `subprocess` is the standard Python approach. PID files enable the dashboard shutdown button to kill processes. `ctx.dispatch_tool("terminal", ...)` would add unnecessary LLM overhead for deterministic process management.

**Alternatives considered:**
- `ctx.dispatch_tool("terminal", ...)` — adds LLM cost for deterministic actions, slower
- In-process imports — Streamlit and Flask would conflict with Hermes' own server, subprocess isolation is safer

### D3: Port selection via env vars with fallback defaults

**Choice:** `HERMES_ANALYTICS_SERVER_PORT` (default 5555) and `HERMES_ANALYTICS_DASHBOARD_PORT` (default 8501). If a port is occupied, the handler increments until finding a free one and reports the actual port.

**Rationale:** Avoids port conflicts when Hermes is already using common ports. The dashboard URL shown to the user reflects the actual port used.

### D4: Snapshot push priority: local → remote → file

**Choice:** The collector tries in order:
1. POST to `http://localhost:{port}/api/snapshots` (local server, if started by slash command)
2. POST to `HERMES_ANALYTICS_REMOTE` (if env var is set)
3. Write `snapshot_latest.json` to repo root (always, as final fallback)

If step 1 or 2 succeeds, step 3 still runs (local file is always written as backup). The collector reports which destinations received the snapshot.

**Rationale:** This ensures data is always saved somewhere. The local server (freshly started) gets the data for immediate dashboard use. The remote server gets it for team aggregation. The local file is the safety net.

### D5: Username resolved from `HERMES_ANALYTICS_USER` env var or hostname fallback

**Choice:** No config file. The collector reads `HERMES_ANALYTICS_USER` env var, falling back to `os.uname().nodename` or `$USER`.

**Rationale:** Hermes plugins shouldn't need a separate config wizard. Environment variables are the standard plugin configuration mechanism (per the `requires_env` field in `plugin.yaml`).

### D6: Dashboard shutdown via "Shutdown Analytics" sidebar button

**Choice:** The local dashboard (`userend/dashboard.py`) has a Streamlit `st.sidebar.button("🛑 Shutdown Analytics")` that:
1. Reads PIDs from `/tmp/hermes-analytics-server.pid` and `/tmp/hermes-analytics-dashboard.pid`
2. Sends `SIGTERM` to each
3. Calls `st.stop()` to end the Streamlit session

**Rationale:** Simple, explicit. Closing the browser tab doesn't kill processes (Streamlit continues in background). Only the button does. This prevents accidental data loss.

### D7: Remote server + dashboard live in `remoteend/`

**Choice:** A new top-level `remoteend/` directory contains:
- `remoteend/server.py` — Flask server with multi-user flat-file persistence (current `server.py`, moved)
- `remoteend/dashboard.py` — Streamlit dashboard with user filter dropdown, user leaderboard page, per-user metrics (new)
- `remoteend/requirements.txt` — dependencies specific to remote deployment

**Rationale:** Clear separation of concerns. The `userend/` plugin is self-contained for a single user. The `remoteend/` is the team/company deployment. Different start commands, different dashboards.

## Risks / Trade-offs

- **Process lifecycle**: If Hermes crashes, orphaned Flask/Streamlit processes may linger. Mitigation: PID files let users manually kill; the dashboard shutdown button works independently.
- **Port conflicts in multi-user environments**: If two users on the same machine run the slash command simultaneously. Mitigation: port auto-increment in D3.
- **Symlink requirement**: Users must symlink `userend/` into `~/.hermes/plugins/`. Mitigation: the slash command handler can detect if the plugin is properly installed and provide clear instructions if not.
- **Streamlit startup latency**: Streamlit takes 2-5 seconds to start. Mitigation: the slash command handler returns an intermediate "Starting dashboard..." message, then updates when ready (or returns the URL immediately since Streamlit serves a loading page).
