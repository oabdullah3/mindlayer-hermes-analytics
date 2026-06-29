---
name: hermes-analytics
description: Guides the agent on using the Hermes Analytics plugin — CLI metrics with dashboard flags, browser dashboard launch, SSH port forwarding for remote machines. Use when the user asks about their Hermes usage, skills, tools, tokens, sessions, or wants to see analytics.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

# Hermes Analytics Plugin

The `mindlayer-hermes-analytics` plugin provides analytics dashboards for Hermes Agent usage — tracking sessions, skills, tools, tokens, shell commands, and Mindlayer skill executions — directly from snapshots of the user's Hermes data directory.

---

## Installation — check first, then offer

**Before suggesting any `hermes snapshot-analytics` command, verify the plugin is installed.** Run:

```bash
hermes plugins list 2>/dev/null | grep -i mindlayer-hermes-analytics
```

If the plugin is **not** installed, tell the user:

> The `mindlayer-hermes-analytics` plugin is not installed yet. Install it with:
>
> ```bash
> hermes plugins install oabdullah3/mindlayer-hermes-analytics
> ```
>
> Then you can run `hermes snapshot-analytics` for your usage dashboards.

If the check fails silently (e.g., `hermes plugins` is not a recognized command), try:

```bash
ls ~/.hermes/plugins/mindlayer-hermes-analytics/__init__.py 2>/dev/null
```

If that file exists, the plugin is installed. If not, guide the user to install it.

Do NOT attempt to install the plugin yourself — the user must run the install command.

---

## How to invoke

### CLI mode (terminal output — works everywhere)

```
hermes snapshot-analytics --mode cli [FLAGS]
```

The `--mode cli` flag is **optional** — it's the default. The output prints directly to the terminal.

### Browser mode (Streamlit dashboard — needs a visual environment)

```
hermes snapshot-analytics --mode browser
```

This starts a Flask server (default port **5555**) and a Streamlit dashboard (default port **8501**), then opens the dashboard in the default browser.

### Both modes

```
hermes snapshot-analytics --mode both
```

Prints CLI metrics **and** launches the browser dashboard.

---

## Dashboard flags (CLI mode)

Use exactly one at a time to get a detailed view for that dashboard:

| Flag | What it shows |
|------|--------------|
| *(no flag)* | General overview — one compact panel per dashboard, each with a hint to drill down |
| `--sessions` | Top 5 sessions by message count, model distribution, platforms |
| `--tokens` | Token totals (input/output/cache/reasoning), top 5 models by usage |
| `--skills` | Top 5 skills by load count, token estimates, bar charts |
| `--tools` | Top 5 tools by call count, bar charts |
| `--commands` | Top 5 most executed and top 5 most failed shell commands |
| `--mindlayer` | Mindlayer skill execution stats, tool/command time rankings, 7-day activity timeline, recent log entries |

**Examples:**

```bash
hermes snapshot-analytics --sessions
hermes snapshot-analytics --skills
hermes snapshot-analytics --mindlayer
```

---

## Browser mode — prerequisites

Before suggesting `--mode browser`, verify ALL of the following:

1. **Visual browser exists** — the user's machine must have a display and a browser installed. If the user is on a headless server or SSH session without X11 forwarding, browser mode will fail.

2. **Port 5555 is free** — the Flask analytics server binds here. If occupied, the plugin auto-increments up to 20 ports (5555–5574).

3. **Port 8501 is free** — the Streamlit dashboard binds here. Same auto-increment behavior (8501–8520).

4. **Dependencies installed** — Flask and Streamlit must be available in the Hermes plugin's Python environment. The plugin auto-installs missing dependencies on first run, but if that fails, run `hermes snapshot-analytics --mode cli` first to trigger the installer.

### When NOT to suggest browser mode

- The user is on a remote SSH session with no display/port forwarding
- The user explicitly asked for "just the numbers" or "quick summary"
- The user's environment has neither a display nor a known browser

---

## SSH port forwarding (remote machines)

If the user is SSH'd into a remote machine that runs Hermes and wants to use the **browser dashboard** from their local machine:

### 1. Start the dashboard on the remote machine

```bash
hermes snapshot-analytics --mode browser
```

Make note of the actual ports used (shown in the output if the defaults were occupied).

### 2. Forward the ports from your local machine

In a **new local terminal** (not the SSH session), run:

```bash
ssh -L 5555:localhost:5555 -L 8501:localhost:8501 user@remote-host
```

Replace `5555` and `8501` with the actual ports if the plugin auto-incremented them.

### 3. Open the dashboard locally

Open `http://localhost:8501` in your local browser. The dashboard communicates with the server through the SSH tunnel.

### Common pitfalls

| Symptom | Likely cause |
|---------|-------------|
| "Connection refused" on localhost:8501 | SSH tunnel not established, or wrong ports |
| Dashboard loads but shows "Cannot connect to API" | Flask server port not forwarded (need BOTH 5555 and 8501) |
| "Address already in use" on remote | Another analytics instance is running — shut it down via the dashboard's **🛑 Shutdown** button, or `kill` the PIDs at `/tmp/hermes-analytics-server.pid` and `/tmp/hermes-analytics-dashboard.pid` |

---

## Slash command (in-session use)

The plugin also registers `/hermes-snapshot-analytics` as an in-session slash command. This works in CLI chats, Telegram, Discord, and any gateway.

```
/hermes-snapshot-analytics
/hermes-snapshot-analytics --sessions
/hermes-snapshot-analytics --mode browser
/hermes-snapshot-analytics --mode both
```

When the user invokes this in a chat session, the plugin:
1. Runs the collector to generate a fresh snapshot
2. In CLI mode: returns the rendered metrics as the response
3. In browser mode: starts the server + dashboard and returns the URL
4. In both mode: returns CLI output + dashboard URL

**Important:** All flags use **ASCII double-hyphens** (`--sessions`), NOT em dashes (`—sessions`). If the user's message contains em dashes, silently normalize them.

---

## When to proactively suggest analytics

Offer to run analytics when the user asks questions like:

- "How many sessions have I had?"
- "Which skills do I use most?"
- "What models am I spending tokens on?"
- "How many tool calls have I made?"
- "Show me my Hermes usage"

Likewise, if a user seems to be debugging their agent usage or wants to understand a performance issue, suggest the relevant dashboard:

- **Slow responses?** → `hermes snapshot-analytics --tokens` (check token/model distribution)
- **Tool errors?** → `hermes snapshot-analytics --tools` or `--commands` (see what's failing)
- **Skill usage questions?** → `hermes snapshot-analytics --skills` (load counts and token estimates)
- **Mindlayer execution issues?** → `hermes snapshot-analytics --mindlayer` (execution status, tool time, recent logs)

---

## Complementary built-in Hermes commands (no plugin needed)

Hermes ships with several built-in CLI commands for session history and insights. These do NOT require the `mindlayer-hermes-analytics` plugin. Use them when the user wants quick answers that don't need the full analytics dashboard:

| Command | What it does |
|---------|-------------|
| `hermes insights` | Summary of recent activity, usage patterns, and tips |
| `hermes sessions list` | List recent sessions with IDs, timestamps, and models |
| `hermes sessions stats` | Aggregate stats across sessions (counts, tokens, tools) |

**When to use which:**

| User asks | Use |
|-----------|-----|
| "Show my recent sessions" | `hermes sessions list` (quick) or `hermes snapshot-analytics --sessions` (full detail) |
| "What's my usage been like?" | `hermes insights` (quick summary) or `hermes snapshot-analytics` (full overview) |
| "How many sessions this week?" | `hermes sessions stats` (quick count) or `hermes snapshot-analytics` (full dashboard) |
| "Which skills do I use most?" | `hermes snapshot-analytics --skills` (plugin required — built-in commands don't cover skills) |
| "How many tool calls?" | `hermes snapshot-analytics --tools` (plugin required — built-in commands don't break down tools) |
| "Token spend by model?" | `hermes snapshot-analytics --tokens` (plugin required — built-in commands don't give model-level detail) |

**Rule of thumb:** For quick session counts and recent activity, use the built-in commands. For skill breakdowns, tool analysis, token-by-model, shell command rankings, or Mindlayer telemetry, you need the plugin.

---

## Dashboard pages (browser mode reference)

When the user asks what a specific dashboard page shows:

| Page | Content |
|------|---------|
| 🏠 Home | Summary cards, top skills & tools, token overview |
| 📋 Session Overview | All sessions: model, tokens, duration, platform |
| 🔍 Session Detail | Deep-dive into one session (messages, tool calls, skills loaded) |
| ⭐ Skills | Skill leaderboard, load counts, token estimates, timeline |
| 🔧 Tools | Tool call counts, pie charts, timeline |
| 🧠 Mindlayer Skills | Log payload telemetry — execution success/failure, tool time, command rankings, 7-day activity heatmap, recent log feed |

---

## Shutdown

The browser dashboard has a **🛑 Shutdown Analytics** button in the sidebar. This kills both the Flask server and the Streamlit dashboard. Closing the browser tab does **not** stop the services — only the button does.

From the terminal, you can also kill manually:

```bash
kill $(cat /tmp/hermes-analytics-server.pid)
kill $(cat /tmp/hermes-analytics-dashboard.pid)
```

---

## Additional flags

| Flag | Purpose |
|------|---------|
| `--mode cli\|browser\|both` | Output mode (default: cli) |
| `--fallback` | If the chosen mode fails, auto-try the other |
| `--server-port N` | Override the Flask server port (default: 5555) |
| `--dashboard-port N` | Override the Streamlit port (default: 8501) |

---

## Stopping a running server between invocations

Before restarting browser mode, shut down any previous instance:

```bash
pkill -f "hermes-analytics/server.py" 2>/dev/null
pkill -f "streamlit run.*dashboard.py" 2>/dev/null
rm -f /tmp/hermes-analytics-server.pid /tmp/hermes-analytics-dashboard.pid
```
