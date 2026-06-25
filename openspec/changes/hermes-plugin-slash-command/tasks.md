## 1. Plugin scaffold

- [ ] 1.1 Create `userend/plugin.yaml` with name, version, description, `provides_commands`, `requires_env`
- [ ] 1.2 Create `userend/__init__.py` with `register(ctx)` function registering `/hermes-snapshot-analytics` slash command
- [ ] 1.3 Create `userend/schemas.py` with slash command parameter schema (optional `--port`, `--dashboard-port` flags)
- [ ] 1.4 Verify plugin is discoverable: symlink `~/.hermes/plugins/hermes-analytics` → repo `userend/`, test `/plugins` in Hermes

## 2. Slash command orchestration handler

- [ ] 2.1 Implement `_handle_snapshot_analytics(raw_args)` in `userend/__init__.py` — the slash command handler
- [ ] 2.2 Implement local server startup: spawn `python3 userend/server.py` via `subprocess.Popen`, write PID to `/tmp/hermes-analytics-server.pid`, wait for health check
- [ ] 2.3 Implement port auto-increment: if default port is occupied, try next port, report actual port
- [ ] 2.4 Implement collector invocation: `subprocess.run` on `python3 userend/collector.py`, pass server port and remote URL via env vars
- [ ] 2.5 Implement local dashboard startup: spawn `streamlit run userend/dashboard.py` via `subprocess.Popen`, write PID to `/tmp/hermes-analytics-dashboard.pid`
- [ ] 2.6 Return success response with dashboard URL and remote dashboard URL (if configured)
- [ ] 2.7 Register `on_session_end` hook (optional) or handle cleanup when session terminates

## 3. Remove old userend install/config system

- [ ] 3.1 Delete `userend/install.sh`
- [ ] 3.2 Delete `userend/hermes-snapshot` bash script
- [ ] 3.3 Delete `userend/test_snapshot_compat.py` (if no longer relevant)

## 4. Update collector for new push priority and env var config

- [ ] 4.1 Remove `read_user_config()` — no more `~/.hermes-analytics.conf` reading
- [ ] 4.2 Add username resolution: read `HERMES_ANALYTICS_USER` env var, fall back to `$USER` or hostname
- [ ] 4.3 Add local server push: POST to `http://localhost:{HERMES_ANALYTICS_SERVER_PORT}/api/snapshots` before remote push
- [ ] 4.4 Add hardcoded remote URL with `HERMES_ANALYTICS_REMOTE` override
- [ ] 4.5 Implement push priority: local server → remote server → local file (all attempted)
- [ ] 4.6 Update collector output messages to report all push results
- [ ] 4.7 Update `userend/collector.py` to accept port/env overrides as CLI args or env vars

## 5. Local dashboard with shutdown button

- [ ] 5.1 Copy/move `dashboard.py` to `userend/dashboard.py` as single-user local dashboard
- [ ] 5.2 Remove multi-user logic from local dashboard (no user dropdown, single snapshot)
- [ ] 5.3 Add "🛑 Shutdown Analytics" button in sidebar
- [ ] 5.4 Implement shutdown: read PIDs from `/tmp/hermes-analytics-{server,dashboard}.pid`, send SIGTERM, then `st.stop()`
- [ ] 5.5 Add confirmation message after shutdown
- [ ] 5.6 Ensure closing browser tab does NOT trigger shutdown

## 6. Local single-user server

- [ ] 6.1 Copy/move `server.py` to `userend/server.py` as single-user local server
- [ ] 6.2 Remove multi-user endpoints from local server (no `/api/users/*`, no leaderboard)
- [ ] 6.3 Local server reads from `snapshot_latest.json` directly (no `server_data/{user}/` directory)
- [ ] 6.4 Keep `/api/health`, `/api/snapshots/latest`, `/api/skills`, `/api/tools`, `/api/sessions` core endpoints

## 7. Create remoteend/ directory

- [ ] 7.1 Create `remoteend/` top-level directory
- [ ] 7.2 Copy current `server.py` to `remoteend/server.py` (multi-user server, unchanged)
- [ ] 7.3 Create `remoteend/dashboard.py` — multi-user Streamlit dashboard
- [ ] 7.4 Add user filter dropdown to remote dashboard (populated from `/api/users`)
- [ ] 7.5 Add "Users" leaderboard page with per-user session/skill/tool rankings
- [ ] 7.6 Add per-user drill-down: clicking a user filters all pages to that user
- [ ] 7.7 Ensure remote dashboard has NO shutdown button

## 8. Root-level cleanup

- [ ] 8.1 Remove or simplify root `collector.py` (keep as optional convenience shim)
- [ ] 8.2 Remove or simplify root `server.py` (keep as optional convenience shim)
- [ ] 8.3 Remove or simplify root `dashboard.py` (keep as optional convenience shim)
- [ ] 8.4 Update root `install.sh` if needed (symlink plugin, install deps)
- [ ] 8.5 Update root `README.md` with new plugin-based usage instructions

## 9. Testing and verification

- [ ] 9.1 Test `/hermes-snapshot-analytics` slash command in Hermes CLI
- [ ] 9.2 Test local dashboard loads and shows data
- [ ] 9.3 Test shutdown button kills server and dashboard processes
- [ ] 9.4 Test remote push (with `HERMES_ANALYTICS_REMOTE` set)
- [ ] 9.5 Test push priority: local server down → remote succeeds → local file written
- [ ] 9.6 Test push priority: all servers down → local file still written
- [ ] 9.7 Test port auto-increment when default ports occupied
- [ ] 9.8 Test remoteend server + dashboard multi-user functionality
- [ ] 9.9 Test that old `~/.hermes-analytics.conf` is ignored
- [ ] 9.10 Run existing test suite to verify no regressions
