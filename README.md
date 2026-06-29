# Hermes Analytics

Track your Hermes Agent — skills, tools, tokens, shell commands, and sessions — right from the chat interface.

---

## Install

```bash
hermes plugins install oabdullah3/mindlayer-hermes-analytics
```

---

## Use

From inside a Hermes chat:

```
/hermes-snapshot-analytics
```

Or from the terminal:

```bash
hermes snapshot-analytics --mode browser    # Streamlit dashboard (default)
hermes snapshot-analytics --mode cli        # terminal summary
hermes snapshot-analytics --mode both       # terminal + dashboard
```

This starts a local server, collects your Hermes data, and serves the output. In browser mode, a Streamlit dashboard URL appears in chat.

| Dashboard page | Shows |
|---|---|
| 🏠 Home | Summary cards, top skills & tools |
| 📋 Session Overview | All sessions with model, tokens, duration |
| 🔍 Session Detail | One session deep-dive |
| ⭐ Skills | Skill usage, token estimates, timeline |
| 🔧 Tools | Tool call counts, pie charts, timeline |
| 🧠 Mindlayer Skills | Log payload telemetry — execution metrics, tool time, command rankings, activity timeline, logs feed |

**CLI output** (`--mode cli`) shows everything above in a compact terminal format:
- Session summary (count, models, platforms, top skills)
- Token totals across all sessions
- Skills ranked by load count
- Tools ranked by call count
- Shell commands ranked by usage
- Mindlayer Skills execution stats (status breakdown, tool time, top commands, timeline, recent logs)

**Shutdown:** Click **🛑 Shutdown Analytics** in the dashboard sidebar.

---

## Configuration (optional)

Environment variables:

| Variable | Default | What it does |
|---|---|---|
| `HERMES_ANALYTICS_USER` | your OS username | Name shown on dashboards |
| `HERMES_ANALYTICS_REMOTE` | _(not set)_ | Push snapshots to a team server |
| `HERMES_HOME` | `~/.hermes` | Custom Hermes data directory |

---

## Uninstall

```bash
hermes plugins uninstall mindlayer-hermes-analytics
```

Then remove any env vars you added (`HERMES_ANALYTICS_USER`, etc.) from your shell profile.

---

## Dev setup (clone & run locally)

If you're hacking on the plugin itself rather than installing it as a user:

```bash
git clone https://github.com/oabdullah3/mindlayer-hermes-analytics.git
cd hermes-analytics
./install.sh                         # deps + symlink into ~/.hermes/plugins/
```

Run components manually:

```bash
python3 server.py &
streamlit run dashboard.py
# or: python3 cli_metrics.py
```

Open **http://localhost:8501**.

