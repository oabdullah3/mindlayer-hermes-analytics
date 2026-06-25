# Hermes Analytics

Track what your Hermes Agent does — skill usage, tool calls, token costs, and session history — without touching Hermes core.

---

## Quickstart (single user, everything local)

You have Hermes Agent running. You want dashboards.

```bash
git clone <this-repo>
cd hermes-analytics
./install.sh
python3 server.py &
streamlit run dashboard.py
```

Open **http://localhost:8501**. Done.

`install.sh` is idempotent — safe to re-run if anything goes wrong.

---

## What you get

Five Streamlit dashboards served at `http://localhost:8501`:

| Page | What you see |
|------|-------------|
| 🏠 **Portal Home** | Summary cards, top-5 skills and tools |
| 📋 **Session Overview** | Every session with model, platform, tokens, duration — filter by model/platform, click to drill in |
| 🔍 **Session Detail** | Everything about one session: skills loaded, tools called, shell commands, errors, messages |
| ⭐ **Skills** | Which skills you use most, token estimates, per-skill timeline, drill-down to sessions |
| ⭐ **Tools** | Tool call counts, pie charts, per-tool timeline, drill-down to sessions |

The data comes from your `~/.hermes/` directory — zero Hermes modifications.

---

## How it works (30 seconds)

```
~/.hermes/state.db  ──→  collector.py  ──→  snapshot_latest.json  ──→  server.py  ──→  dashboard.py
```

1. The **collector** reads your Hermes data and produces one JSON file
2. The **server** serves that JSON over a REST API
3. The **dashboard** (Streamlit) reads the API and renders charts

You can run the collector again anytime to refresh the data:

```bash
python3 collector.py
```

---

## Using with your Hermes agent

The `userend/` directory is what you drop into any machine running Hermes.

### One-time setup

```bash
cd hermes-analytics
./userend/install.sh
```

This prompts for:
- **Your username** — any name you want to appear on dashboards
- **Remote server URL** — leave blank if you're running everything locally

It writes `~/.hermes-analytics.conf`:

```
HERMES_ANALYTICS_USER=alice
HERMES_ANALYTICS_REMOTE=https://hermes-dash.example.com
```

### Run the collector

```bash
# From the repo root:
python3 userend/collector.py

# Or use the slash command from anywhere:
./userend/hermes-snapshot

# With dashboard URL in output:
./userend/hermes-snapshot dashboard
```

The collector reads `~/.hermes/state.db` and `~/.hermes/log_payloads/`, produces `snapshot_latest.json` (or pushes to the remote if configured).

### Custom Hermes location

```bash
HERMES_HOME=/custom/path python3 userend/collector.py
```

---

## Remote setup (team dashboard)

You want one dashboard showing analytics from multiple people.

### Server side (one machine)

```bash
git clone <this-repo>
cd hermes-analytics
./install.sh
python3 server.py
```

The server listens on port 5555. Snapshots arrive via POST and are stored in `server_data/{username}/`. No database needed.

Start the dashboard on the same machine:

```bash
streamlit run dashboard.py
```

### User side (each person's machine)

Run `./userend/install.sh` on each machine. When it asks for the remote URL, enter the server's address:

```
http://your-server:5555
```

This writes `HERMES_ANALYTICS_REMOTE` to `~/.hermes-analytics.conf`. The collector will now POST to the server instead of writing local files.

To run the collector:

```bash
./userend/hermes-snapshot
```

That's it. Each user's analytics appear on the shared dashboard.

### Environment variables reference

| Variable | Where to set it | What it does |
|----------|----------------|--------------|
| `HERMES_ANALYTICS_USER` | `~/.hermes-analytics.conf` | Your name on the dashboard |
| `HERMES_ANALYTICS_REMOTE` | `~/.hermes-analytics.conf` | Server URL to push to (omit for local mode) |
| `HERMES_HOME` | Environment variable | Custom Hermes data directory (default: `~/.hermes`) |
| `PORT` | Environment variable | Server port (default: `5555`) |

---

## Running tests

```bash
pip install -r requirements.txt
python3 -m pytest tests/ -v
```

42 tests (collector, API, schema validation), all isolated from real Hermes data.

---

## License

MIT
