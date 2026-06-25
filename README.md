# Hermes Analytics

**External analytics dashboard for Hermes Agent** — track skill usage, tool calls, session costs, and conversation patterns without touching Hermes core.

### Why

Hermes Agent produces rich usage data (SQLite, JSONL logs, tool payloads) but nothing aggregates or visualizes it. Hermes Analytics reads that data, enriches it, and serves it through a REST API and Streamlit dashboards — zero modifications to Hermes itself.

**Key selling points:**
- 🔌 **Zero Hermes modifications** — purely external consumer
- 🐍 **Pure Python** — no external services, no Docker required
- 🌐 **Remote-deployable** — single-user local, or multi-user team dashboard
- ⚡ **One-command setup** — `./install.sh` brings up everything

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR MACHINE                                 │
│                                                                  │
│  ~/.hermes/ (state.db, sessions/*.jsonl, logs/agent.log)         │
│  ~/.hermes-analytics.conf  (HERMES_ANALYTICS_USER=alice)         │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────┐         POST /api/snapshots                │
│  │ userend/         │ ──────────────────────────────┐            │
│  │  ├ collector.py  │      (with username,          │            │
│  │  ├ install.sh    │       Mode B)                 │            │
│  │  └ hermes-snapshot                               │            │
│  └──────────────────┘                               │            │
│       │                                             │            │
│       │ /hermes-snapshot (agent slash command)      │            │
│       ▼                                             │            │
│  ┌────────────┐       ┌─────────────────────────────┘            │
│  │ server.py  │◄──────┘                                         │
│  │ (Flask API)│                                                  │
│  └────────────┘                                                  │
│       │                                                          │
│       │ server_data/{user}/snapshot_*.json (flat-file)           │
│       ▼                                                          │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Streamlit Dashboard (dashboard.py)                         │   │
│  │                                                             │   │
│  │ Pages:                                                      │   │
│  │   🏠 Portal Home      📋 Session Overview                   │   │
│  │   ⭐ Skills Analytics  🔧 Tools Analytics                   │   │
│  │   🔍 Session Detail                                         │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Two modes

| Mode | Description | Network |
|------|-------------|---------|
| **A — Local** | Everything on one machine. Collector writes local JSON, server reads it, dashboard queries the API. | None needed |
| **B — Remote** | Multiple users push snapshots to a shared server. Each user configures `~/.hermes-analytics.conf` with username and remote URL. | HTTPS |

---

## Setup

### One-command install

```bash
git clone <this-repo>
cd hermes-analytics
./install.sh
```

`install.sh` does four things:
1. Checks Python 3 and pip are available
2. Installs dependencies from `requirements.txt` (skips if already installed)
3. Runs `userend/install.sh` to configure username and optional remote server
4. Runs `python3 collector.py` to generate the initial `snapshot_latest.json`

It's idempotent — safe to re-run after partial failures or upgrades.

### Start services

```bash
python server.py &                # REST API on port 5555
streamlit run dashboard.py        # Dashboard on http://localhost:8501
```

### Remote setup (Mode B)

For team dashboards where multiple users push to a shared server:

1. **On the server:** clone the repo, run `./install.sh`, start `python server.py` on a reachable interface
2. **On each user machine:** run `./userend/install.sh`, enter username and the server's URL. The collector will POST to the server instead of writing local files.
3. All user snapshots are stored at `server_data/{username}/snapshot_*.json` on the server.

---

## Userend client (`userend/`)

The `userend/` directory is the self-contained, installable client that each Hermes Agent user deploys.

```bash
# One-time setup — prompts for username and optional server URL
./userend/install.sh

# Collect analytics and show inline summary
./userend/hermes-snapshot

# Same + dashboard URL
./userend/hermes-snapshot dashboard

# Run collector directly
python3 userend/collector.py
```

### Config file (`~/.hermes-analytics.conf`)

Shell-sourceable key=value format, created by `userend/install.sh`:

```bash
HERMES_ANALYTICS_USER=alice
HERMES_ANALYTICS_REMOTE=https://hermes-dash.example.com
```

The collector reads this on every run. `HERMES_ANALYTICS_USER` is included in remote push POST bodies.

---

## What the collector extracts

The collector runs a 9-step pipeline against `~/.hermes/`:

| Step | What | Source |
|------|------|--------|
| 1. Sessions | All sessions with platform, model, token totals, message counts | `state.db` → `sessions` table |
| 2. Skill loads | Every `skill_view`/`skill_manage` invocation with skill name and load timestamp | `state.db` → `messages` table |
| 3. Preceding messages | The user message that triggered each skill load | `state.db` → `messages` (id − 1) |
| 4. Tool calls | Aggregated per-tool counts per session | `state.db` → `messages` (role=tool) |
| 5. Shell commands | Every terminal command executed, with exit code, output (truncated to 200 chars), and success/failure status | `state.db` → `messages` (tool_calls JSON) |
| 6. Token estimation | `CEIL(content_chars / 4)` per skill (Hermes doesn't populate per-message tokens) | Tool response content |
| 7. User messages | All user messages per session, truncated to 200 chars | `state.db` → `messages` (role=user) |
| 8. Errors | `Tool terminal returned error` lines with session and duration | `logs/agent.log` |
| 9. Log payloads | CLI tool audit telemetry: duration, command, status, result size, workflow metadata | `log_payloads/YYYY-MM-DD/*.json` |

Output: `snapshot_latest.json` — a self-contained JSON artifact with all sessions, skills, tools, shell commands, errors, and global insights.

### Quick start (collector only)

```bash
# Run the collector (reads ~/.hermes/ by default)
python collector.py

# Custom Hermes location
HERMES_HOME=/custom/path python collector.py

# Push to a remote server instead of writing local file
HERMES_ANALYTICS_REMOTE=https://dash.example.com python collector.py
```

---

## API endpoints (REST API)

The server exposes a JSON-only API on port 5555. Multi-user flat-file persistence per ADR-0002.

### Core endpoints

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `GET` | `/api/health` | Health check — returns `{"status":"ok","users":N,"total_sessions":N}` if data loaded, 503 otherwise | ✅ |
| `GET` | `/api/snapshots/latest` | All users' latest snapshots (add `?username=` to filter) | ✅ |
| `POST` | `/api/snapshots` | Accept snapshot from remote collector — requires `username` field, writes to `server_data/{user}/snapshot_{ts}.json` | ✅ |
| `GET` | `/api/skills` | All skills aggregated across users (add `?username=` to filter) | ✅ |
| `GET` | `/api/skills/:name` | Single skill detail with per-user, per-session breakdown | ✅ |
| `GET` | `/api/tools` | All tools aggregated across users (add `?username=` to filter) | ✅ |
| `GET` | `/api/tools/:name` | Single tool detail with per-user, per-session call counts | ✅ |
| `GET` | `/api/sessions` | All sessions from all users' latest snapshots (add `?username=` to filter) | ✅ |
| `GET` | `/api/sessions/:id` | Full session detail (includes `_username` field) | ✅ |
| `POST` | `/api/refresh` | Trigger collector re-run, returns aggregated status | ✅ |

### Multi-user endpoints (ADR-0002)

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `GET` | `/api/users` | List all usernames with snapshot counts | ✅ |
| `GET` | `/api/users/:username/latest` | Most recent snapshot for a user | ✅ |
| `GET` | `/api/users/:username/history` | All snapshot timestamps for a user (newest first) | ✅ |
| `GET` | `/api/users/:username/:timestamp` | Specific historical snapshot by timestamp | ✅ |
| `GET` | `/api/leaderboard/sessions` | All users ranked by session count | ✅ |
| `GET` | `/api/leaderboard/skills` | All users ranked by skill load count | ✅ |
| `GET` | `/api/leaderboard/tools` | All users ranked by tool call count | ✅ |

### Quick start (API)

```bash
pip install -r requirements.txt
python server.py                    # starts on port 5555
curl localhost:5555/api/health      # health check
```

### Quick start (tests)

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v         # runs all tests with verbose output
```

### Test coverage

The test suite runs 42 tests across 3 categories:

| Category | File | Tests | Description |
|----------|------|-------|-------------|
| **Collector** | `tests/test_collector.py` | 11 | Session extraction, skill load detection, preceding messages, tool aggregation, token estimation, user messages, error parsing, global insights, missing sources |
| **API** | `tests/test_api.py` | 24 | Health check, snapshots, skills endpoints, tools endpoints, sessions endpoints, snapshot POST ingestion (valid/invalid/missing), refresh trigger |
| **Schema** | `tests/test_schema.py` | 7 | Top-level keys, ISO 8601 timestamp, session object structure, empty arrays for blank sessions, global insights structure, skill load fields, tool call fields |

**Key properties:**
- 🏃 **Fast:** all 42 tests complete in < 1 second
- 🔒 **Isolated:** no test touches the real `~/.hermes/` directory — uses `tmp_path` fixtures
- 🧩 **Synthetic:** a programmatic `state.db` with 3 sessions (telegram/discord/cli), 37 messages, and 3 distinct tool types exercises every collector code path
- ✅ **Deterministic:** known fixture data means tests never depend on real Hermes state

---

## Dashboards (Streamlit)

Five dashboard pages served by `dashboard.py`, read from the REST API:

| Page | Content | Status |
|------|---------|--------|
| 🏠 **Portal Home** | Cross-domain summary cards, sidebar navigation, top-5 skills/tools previews | ✅ |
| 📋 **Session Overview** | Sessions per day & by model charts, model/platform filters, session table with click-to-select | ✅ |
| 🔍 **Session Detail** | Per-session skills, tools, shell commands, errors, user messages; dropdown picker | ✅ |
| ⭐ **Skills Analytics** | Ranking table, bar chart, token histogram, stacked timeline, preceding messages, skill drill-down | ✅ |
| ⭐ **Tools Analytics** | Ranking table, call distribution (pie), stacked timeline, session histogram, tool drill-down | ✅ |

### Quick start (dashboard)

```bash
pip install -r requirements.txt
streamlit run dashboard.py          # starts on http://localhost:8501
```

---

## Project status

| Component | File | Status |
|-----------|------|--------|
| Collector | `userend/collector.py` | ✅ implemented |
| REST API server (multi-user) | `server.py` | ✅ implemented |
| Userend client | `userend/` (install.sh, hermes-snapshot, collector) | ✅ implemented |
| Streamlit dashboards | `dashboard.py` | ✅ |
| Installer | `userend/install.sh` | ✅ implemented |
| Test suite | `tests/` (42 tests) | ✅ implemented |

---

## Deployment scenarios

| Scenario | Collector | Server | Dashboard | Users |
|----------|-----------|--------|-----------|-------|
| **Dev / single user** | Same machine | Same machine | Same machine | 1 |
| **Team dashboard** | Each user's machine → push | Shared VPS | Shared VPS | 2–20 |
| **Cloud dashboard** | Each user's machine → push | Cloud VM (fly.io, Railway) | Cloud VM | 2–100+ |
| **Read-only viewer** | N/A | Cloud VM | Cloud VM (public) | ∞ |

---

## Configuration

| Env / Config | Purpose | Default |
|-------------|---------|---------|
| `HERMES_HOME` | Path to Hermes data directory | `~/.hermes` |
| `HERMES_ANALYTICS_REMOTE` | Remote server URL for push mode (env var or `~/.hermes-analytics.conf`) | (unset — local mode) |
| `HERMES_ANALYTICS_USER` | Username for multi-user push mode (`~/.hermes-analytics.conf`) | (unset) |
| `PORT` | REST API server port | `5555` |

---

## Roadmap / Open questions

- [x] Streamlit dashboards (`dashboard.py`) — 5 interactive pages (Portal Home, Session Overview, Session Detail, Skills, Tools)
- [x] Multi-user server (flat-file persistence per ADR-0002)
- [x] `userend/` client restructuring (slash commands, config per ADR-0001)
- [x] `install.sh` — one-command setup
- [x] Log payloads analytics (Step 9 in collector)
- [ ] Per-message token counts (blocked: Hermes doesn't populate this column)
- [ ] Auto-load vs. manual skill detection (blocked: Hermes doesn't expose this distinction)
- [ ] Incremental collection (only new sessions since last run)

---

## File structure

```
hermes-analytics/
├── install.sh                  # One-command setup (idempotent)
├── collector.py                # Deprecation wrapper → userend.collector
├── server.py                   # Flask REST API (multi-user)
├── dashboard.py                # Streamlit dashboards (5 pages)
├── requirements.txt            # Python dependencies
├── snapshot_latest.json        # Local mode snapshot (auto-generated)
├── README.md
├── userend/                    # User-side client (installed per Hermes user)
│   ├── install.sh              # Config wizard (username, remote URL)
│   ├── hermes-snapshot         # Agent slash-command script
│   ├── collector.py            # Main collector (9-step pipeline)
│   └── test_snapshot_compat.py # Backward-compat verification
├── server_data/                # Multi-user flat-file storage (Mode B)
│   └── {username}/
│       └── snapshot_*.json
├── tests/                      # Test suite (42 tests)
│   ├── conftest.py             # Synthetic fixture DB builder
│   ├── test_collector.py       # 11 collector tests
│   ├── test_api.py             # 24 API tests
│   └── test_schema.py          # 7 schema validation tests
└── openspec/                   # Design documentation (ADR, specs)
    ├── config.yaml
    ├── specs/                  # 22 capability specs
    └── changes/                # Archived change proposals
```

---

## License

MIT
