# Hermes Analytics

Track what your Hermes Agent does — skill usage, tool calls, token costs, shell commands, and session history — without touching Hermes core.

---

## Quickstart (single user, everything local)

You have Hermes Agent running. You want dashboards. Use the slash command:

```
/hermes-snapshot-analytics
```

That's it. Hermes Analytics starts a local server, collects your data, and launches a dashboard. The URL appears in chat.

Or run it manually:

```bash
git clone <this-repo>
cd hermes-analytics
./install.sh
python3 userend/server.py &
streamlit run userend/dashboard.py
```

Open **http://localhost:8501**. Done.

---

## What you get

Five Streamlit dashboards served at `http://localhost:8501`:

| Page | What you see |
|------|-------------|
| 🏠 **Portal Home** | Summary cards, top-5 skills and tools |
| 📋 **Session Overview** | Every session with model, platform, tokens, duration — filter by model/platform, click to drill in |
| 🔍 **Session Detail** | Everything about one session: skills loaded, tools called, shell commands, errors, messages |
| ⭐ **Skills** | Which skills you use most, token estimates, per-skill timeline, drill-down to sessions |
| 🔧 **Tools** | Tool call counts, pie charts, per-tool timeline, drill-down to sessions |

The data comes from your `~/.hermes/` directory — zero Hermes modifications.

---

## How it works (30 seconds)

```
~/.hermes/state.db  ──→  userend/collector.py  ──→  userend/server.py  ──→  userend/dashboard.py
                  ──→  snapshot_latest.json (file fallback)
                  ──→  remoteend/server.py (optional multi-user)
```

1. The **collector** reads your Hermes data and produces a JSON snapshot
2. The **server** serves that JSON over a REST API
3. The **dashboard** (Streamlit) reads the API and renders charts

You can refresh the data anytime with the slash command or `python3 userend/collector.py`.

---

## Slash command: `/hermes-snapshot-analytics`

From inside a Hermes chat session:

```
/hermes-snapshot-analytics
```

What happens:

1. Starts a local Flask server on port 5555 (auto-increments if occupied)
2. Runs the collector — pushes to local server, then remote (if configured), then writes local file
3. Starts a Streamlit dashboard on port 8501
4. Returns the dashboard URL in chat

Optional parameters:

```
/hermes-snapshot-analytics --server-port=5556 --dashboard-port=8502
```

Shut down all analytics processes with the **🛑 Shutdown Analytics** button in the dashboard sidebar.

---

## Configuration

All configuration is via **environment variables** (no config files).

| Variable | Default | Purpose |
|----------|---------|---------|
| `HERMES_ANALYTICS_USER` | `$USER` or hostname | Your name on dashboards |
| `HERMES_ANALYTICS_REMOTE` | _(not set)_ | Remote server URL for push |
| `HERMES_HOME` | `~/.hermes` | Custom Hermes data directory |

Set them in your shell profile:

```bash
export HERMES_ANALYTICS_USER="alice"
export HERMES_ANALYTICS_REMOTE="https://hermes-dash.example.com"
```

> **Note:** The old `~/.hermes-analytics.conf` file is no longer read. Migrate to env vars.

---

## Project structure

```
hermes-analytics/
├── userend/              # Plugin + local single-user stack
│   ├── plugin.yaml       # Hermes plugin manifest
│   ├── __init__.py       # Slash command handler
│   ├── schemas.py        # Slash command parameter schemas
│   ├── collector.py      # 9-step data extraction pipeline
│   ├── server.py         # Single-user Flask REST API
│   └── dashboard.py      # Single-user Streamlit dashboard
├── remoteend/            # Multi-user shared stack
│   ├── server.py         # Multi-user Flask REST API
│   └── dashboard.py      # Multi-user dashboard (user filter + leaderboard)
├── tests/                # Pytest test suite
├── install.sh            # One-command setup
└── requirements.txt      # Python dependencies
```

Root `collector.py`, `server.py`, and `dashboard.py` are backward-compatible shims.

---

## Remote setup (team dashboard)

You want one dashboard showing analytics from multiple people.

### Server side (one machine)

```bash
git clone <this-repo>
cd hermes-analytics
./install.sh
python3 remoteend/server.py
```

Start the multi-user dashboard:

```bash
streamlit run remoteend/dashboard.py
```

The remote dashboard includes a **user filter dropdown** and a **leaderboard** ranking users by sessions, tokens, and tool calls.

### User side (each person's machine)

Set the remote URL in each user's environment:

```bash
export HERMES_ANALYTICS_USER="alice"
export HERMES_ANALYTICS_REMOTE="http://your-server:5555"
```

Then use `/hermes-snapshot-analytics` in Hermes, or run:

```bash
python3 userend/collector.py
```

The collector pushes to the remote server. Each user's analytics appear on the shared dashboard.

---

## Push priority

The collector always tries all push targets in order:

1. **Local server** (`http://localhost:5555`) — started by the slash command
2. **Remote server** (if `HERMES_ANALYTICS_REMOTE` is set)
3. **Local file** (`snapshot_latest.json`) — always written as safety net

All three are attempted regardless of individual failures.

---

## Running tests

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

Tests cover collector pipeline, API endpoints, and schema validation. All tests use a synthetic database — no real Hermes data required.

---

## Plugin installation

The `install.sh` script creates a symlink:

```
~/.hermes/plugins/hermes-analytics → userend/
```

Hermes discovers the plugin automatically. Verify with `/plugins` in a Hermes chat.

Manual installation:

```bash
mkdir -p ~/.hermes/plugins
ln -sf /path/to/hermes-analytics/userend ~/.hermes/plugins/hermes-analytics
```

---

## License

MIT
