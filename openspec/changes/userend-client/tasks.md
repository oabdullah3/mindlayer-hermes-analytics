## 1. userend/ directory structure

- [ ] 1.1 Create `userend/` directory at repo root
- [ ] 1.2 Create `userend/__init__.py` (empty, makes it a Python package)
- [ ] 1.3 Create `userend/README.md` documenting Python-sufficiency decision and component overview

## 2. Move collector to userend/

- [ ] 2.1 Copy `collector.py` to `userend/collector.py` (identical, no modifications yet)
- [ ] 2.2 Verify `python3 userend/collector.py` runs and produces valid `snapshot_latest.json`
- [ ] 2.3 Update internal imports in `userend/collector.py` if any relative paths changed
- [ ] 2.4 Add `HERMES_ANALYTICS_USER` reading from `~/.hermes-analytics.conf` in collector initialization
- [ ] 2.5 Add `username` field to remote push POST body when `HERMES_ANALYTICS_USER` is configured

## 3. Snapshot backward compatibility

- [ ] 3.1 Create `userend/test_snapshot_compat.py` with JSON deep-compare logic
- [ ] 3.2 Implement `generated_at` normalization (exclude from comparison, normalize to constant)
- [ ] 3.3 Run test: old root collector vs new userend collector against same `HERMES_HOME`
- [ ] 3.4 Verify all fields match: sessions, global_insights, tokens, stats, skills_loaded, tool_calls, shell_commands, user_messages, errors
- [ ] 3.5 Verify remote push POST body is identical between old and new collector
- [ ] 3.6 Verify CLI arguments (`--hermes-home`, `--output`) work identically from userend path

## 4. Root deprecation wrapper

- [ ] 4.1 Replace root `collector.py` with deprecation wrapper that imports from `userend.collector`
- [ ] 4.2 Wrapper prints deprecation notice to stderr: "collector.py moved to userend/collector.py"
- [ ] 4.3 Verify `python collector.py` at repo root still produces valid snapshot (via wrapper)
- [ ] 4.4 Verify `HERMES_ANALYTICS_REMOTE` mode works through the wrapper

## 5. Agent slash commands

- [ ] 5.1 Create `userend/hermes-snapshot` shell script (shebang, set -euo pipefail)
- [ ] 5.2 Script sources `~/.hermes-analytics.conf` for HERMES_ANALYTICS_USER and HERMES_ANALYTICS_REMOTE
- [ ] 5.3 Script runs `python3 userend/collector.py` from the repo root
- [ ] 5.4 Script parses collector output and prints inline summary (sessions, skills, tools, shell commands, errors)
- [ ] 5.5 Implement `dashboard` subcommand: prints dashboard URL after summary
- [ ] 5.6 Handle missing config file: print "Run userend/install.sh first" and exit 1
- [ ] 5.7 Handle collection failure: print error summary and exit with collector's exit code
- [ ] 5.8 Make script executable: `chmod +x userend/hermes-snapshot`

## 6. User config setup (install.sh)

- [ ] 6.1 Create `userend/install.sh` with shebang, `set -euo pipefail`, color-coded output
- [ ] 6.2 Prompt for username: "Enter your username for Hermes Analytics:"
- [ ] 6.3 Write `HERMES_ANALYTICS_USER=<input>` to `~/.hermes-analytics.conf`
- [ ] 6.4 Prompt for remote URL: "Analytics server URL? [skip for local-only]:" (optional)
- [ ] 6.5 Write `HERMES_ANALYTICS_REMOTE=<url>` if provided
- [ ] 6.6 Idempotency: if config exists, show current settings without overwriting
- [ ] 6.7 Add `--reconfigure` flag to force re-prompt
- [ ] 6.8 Make `userend/hermes-snapshot` executable during install
- [ ] 6.9 Print post-install summary: username, remote URL (if set), slash command to use

## 7. Server.py refresh endpoint update

- [ ] 7.1 Update `POST /api/refresh` to call `python3 userend/collector.py` instead of `python3 collector.py`
- [ ] 7.2 Verify refresh endpoint works end-to-end: trigger → collector runs → snapshot reloaded

## 8. Multi-user server (ADR-0002 compliance)

- [ ] 8.1 Remove in-memory `_SNAPSHOT` variable; replace with flat-file read-on-demand pattern
- [ ] 8.2 Implement `POST /api/snapshots` per ADR-0002: validate `username` field, create `server_data/{username}/` directory, write timestamped snapshot JSON, return 201
- [ ] 8.3 Implement `GET /api/users` — list all usernames with snapshot counts
- [ ] 8.4 Implement `GET /api/users/<username>/latest` — most recent snapshot for a user
- [ ] 8.5 Implement `GET /api/users/<username>/history` — list all snapshots with timestamps
- [ ] 8.6 Implement `GET /api/users/<username>/<timestamp>` — specific historical snapshot
- [ ] 8.7 Implement `GET /api/leaderboard/sessions` — all users ranked by session count
- [ ] 8.8 Implement `GET /api/leaderboard/skills` — all users ranked by skill loads
- [ ] 8.9 Implement `GET /api/leaderboard/tools` — all users ranked by tool calls
- [ ] 8.10 Add `?username=` query parameter to `/api/skills`, `/api/tools`, `/api/sessions`, `/api/sessions/:id`
- [ ] 8.11 Without `?username=`, existing endpoints aggregate across all users
- [ ] 8.12 Preserve single-user local mode: when `server_data/` is empty, fall back to reading `snapshot_latest.json` (existing behavior)
- [ ] 8.13 Add `server_data/` to `.gitignore`

## 9. Documentation & final verification

- [ ] 9.1 Update root `README.md` to reference `userend/` as the user-side client
- [ ] 9.2 Update architecture diagram to show `userend/` directory and `server_data/` directory
- [ ] 9.3 Add `~/.hermes-analytics.conf` documentation to README config section
- [ ] 9.4 Document new multi-user API endpoints in README API reference table
- [ ] 9.5 Run full compat test: `python3 userend/test_snapshot_compat.py` must pass
- [ ] 9.6 Run `userend/install.sh` end-to-end on a clean state
- [ ] 9.7 Run `userend/hermes-snapshot` and verify inline summary output
- [ ] 9.8 Run `userend/hermes-snapshot dashboard` and verify dashboard URL in output
- [ ] 9.9 Verify server.py starts and serves snapshot from userend collector
- [ ] 9.10 Verify `POST /api/snapshots` with username creates `server_data/alice/snapshot_*.json`
- [ ] 9.11 Verify `GET /api/users` returns correct user list
- [ ] 9.12 Verify `GET /api/leaderboard/sessions` ranks users correctly
