# Hermes Analytics

**External analytics dashboard for Hermes Agent** — track skill usage, tool calls, session costs, and conversation patterns without touching Hermes core.

### Why

Hermes Agent produces rich usage data (SQLite, JSONL logs, tool payloads) but nothing aggregates or visualizes it. Hermes Analytics reads that data, enriches it, and serves it through Grafana dashboards — zero modifications to Hermes itself.

**Key selling points:**
- 🔌 **Zero Hermes modifications** — purely external consumer
- 📊 **Grafana-powered dashboards** — industry-standard telemetry frontend
- 🌐 **Remote-deployable** — single-user local, or multi-user team dashboard
- ⚡ **One-command setup** — `./install.sh` brings up everything

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR MACHINE                                 │
│                                                                  │
│  ~/.hermes/ (state.db, sessions/*.jsonl, logs/agent.log)         │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────┐    POST /api/snapshots  (Mode B)               │
│  │ collector.py │ ──────────────────────────────┐                │
│  └──────────────┘                               │                │
│       │                                         │                │
│       │ writes snapshot_latest.json             │                │
│       ▼                                         │                │
│  ┌──────────┐   REST API (Flask, port 5555)     │                │
│  │ server.py│◄──────────────────────────────────┘                │
│  └──────────┘                                                   │
│       │                                                          │
│       │  GET /api/skills, /api/tools, /api/sessions              │
│       │  GET /api/snapshots/latest                               │
│       ▼                                                          │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Grafana (localhost:3000)                                   │   │
│  │                                                             │   │
│  │ Dashboards:                                                 │   │
│  │   ⭐ Skills Analytics    ⭐ Tools Analytics                  │   │
│  │   📋 Session Overview    🔍 Session Detail                  │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Two modes

| Mode | Description | Network |
|------|-------------|---------|
| **A — Local** | Everything on one machine. Collector writes local JSON, server reads it, Grafana queries the API. | None needed |
| **B — Remote** | Multiple users push snapshots to a shared server. Set `HERMES_ANALYTICS_REMOTE=https://dash.example.com` per machine. | HTTPS |

---

## What the collector extracts

The collector runs an 8-step pipeline against `~/.hermes/`:

| Step | What | Source |
|------|------|--------|
| 1. Sessions | All sessions with platform, model, token totals, message counts | `state.db` → `sessions` table |
| 2. Skill loads | Every `skill_view`/`skill_manage` invocation with skill name and load timestamp | `state.db` → `messages` table |
| 3. Preceding messages | The user message that triggered each skill load | `state.db` → `messages` (id − 1) |
| 4. Tool calls | Aggregated per-tool counts per session | `state.db` → `messages` (role=tool) |
| 5. Shell commands | Every terminal command executed, with exit code, output (truncated to 500 chars), and success/failure status | `state.db` → `messages` (tool_calls JSON) |
| 6. Token estimation | `CEIL(content_chars / 4)` per skill (Hermes doesn't populate per-message tokens) | Tool response content |
| 7. User messages | All user messages per session, truncated to 200 chars | `state.db` → `messages` (role=user) |
| 8. Errors | `Tool terminal returned error` lines with session and duration | `logs/agent.log` |

Output: `snapshot_latest.json` — a self-contained JSON artifact with all sessions, skills, tools, shell commands, errors, and global insights (including aggregate command statistics).

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

The server exposes a JSON-only API on port 5555:

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `GET` | `/api/health` | Health check — returns `{"status":"ok"}` if snapshot loaded | ⬜ planned |
| `GET` | `/api/snapshots/latest` | Full snapshot JSON | ⬜ planned |
| `POST` | `/api/snapshots` | Accept snapshot from remote collector | ⬜ planned |
| `GET` | `/api/skills` | All skills, sorted by load count | ⬜ planned |
| `GET` | `/api/skills/:name` | Single skill detail with per-session data | ⬜ planned |
| `GET` | `/api/tools` | All tools, sorted by call count | ⬜ planned |
| `GET` | `/api/tools/:name` | Single tool detail | ⬜ planned |
| `GET` | `/api/sessions` | All sessions, newest first | ⬜ planned |
| `GET` | `/api/sessions/:id` | Full session detail | ⬜ planned |
| `POST` | `/api/refresh` | Trigger collector re-run, return fresh snapshot | ⬜ planned |

### Quick start (API)

```bash
pip install flask
python server.py                    # starts on port 5555
curl localhost:5555/api/health      # health check
```

---

## Dashboards (Grafana)

Four provisioned dashboards — no UI clicking to set up:

| Dashboard | Panels | Source |
|-----------|--------|--------|
| ⭐ **Skills Analytics** | Leaderboard, timeline, token cost table, histogram, weekly trend, auto-vs-manual pie | Infinity (REST API) |
| ⭐ **Tools Analytics** | Leaderboard, timeline, duration table, error stat, co-occurrence heatmap, terminal breakdown | Infinity (REST API) |
| **Session Overview** | Session count, token/cost time series, session table, platform pie, model bar gauge | Infinity (REST API) |
| **Session Detail** | Session header, token breakdown, skills loaded table, tool calls bar chart, user messages, errors panel | Infinity (REST API) |

Grafana URL: `http://localhost:3000` (default credentials: admin/admin)

---

## Project status

| Component | File | Status |
|-----------|------|--------|
| Data collector | `collector.py` | ✅ implemented |
| REST API server | `server.py` | ⬜ planned |
| Grafana dashboards | `grafana/provisioning/` | ⬜ planned |
| Installer | `install.sh` | ⬜ planned |
| Test suite | `tests/` | ⬜ planned |
| README | `README.md` | ✅ you're reading it |

---

## Deployment scenarios

| Scenario | Collector | Server | Grafana | Users |
|----------|-----------|--------|---------|-------|
| **Dev / single user** | Same machine | Same machine | Same machine | 1 |
| **Team dashboard** | Each user's machine → push | Shared VPS | Shared VPS | 2–20 |
| **Cloud dashboard** | Each user's machine → push | Cloud VM (fly.io, Railway) | Cloud VM | 2–100+ |
| **Read-only viewer** | N/A | Cloud VM | Cloud VM (public) | ∞ |

---

## Configuration

| Env variable | Purpose | Default |
|-------------|---------|---------|
| `HERMES_HOME` | Path to Hermes data directory | `~/.hermes` |
| `HERMES_ANALYTICS_REMOTE` | Remote server URL for push mode | (unset — local mode) |
| `PORT` | REST API server port | `5555` |

---

## Roadmap / Open questions

- [ ] REST API server (`server.py`) — next up
- [ ] Grafana dashboards (4 provisioned JSON dashboards)
- [ ] `install.sh` — one-command setup
- [ ] Test suite (pytest with synthetic fixtures)
- [ ] Per-message token counts (blocked: Hermes doesn't populate this column)
- [ ] Auto-load vs. manual skill detection (blocked: Hermes doesn't expose this distinction)
- [ ] Incremental collection (only new sessions since last run)
- [ ] Multi-tenancy support for team dashboards

---

## License

MIT
