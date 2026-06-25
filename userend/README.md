# userend/ — User-Side Hermes Analytics Client

## What is this?

The `userend/` directory is the installable, self-contained client that each
Hermes Agent user deploys to push analytics data to a shared dashboard server.

## Design Decision: Python stays

The collector is implemented in **Python 3**, not Node.js. Here's why:

- **Zero native compilation**: The collector uses only Python stdlib — `sqlite3`,
  `json`, `os`, `re`, `math`, `argparse`, `sys`, `datetime`. The only optional
  dependency is `requests` (for remote push mode).
- **Hermes is Python**: Hermes Agent itself is Python-based. A Python collector
  means zero additional runtimes to install.
- **Node.js would add complexity**: `better-sqlite3` (the Node equivalent) requires
  native C++ compilation and platform-specific binaries. No benefit.
- **Performance is a non-issue**: Snapshot generation completes in under 2 seconds
  for hundreds of sessions. No JIT compilation needed.

## Components

| File | Purpose |
|------|---------|
| `collector.py` | The data collector — reads Hermes state.db, produces snapshot JSON |
| `install.sh` | User-side setup — prompts for username, writes `~/.hermes-analytics.conf` |
| `hermes-snapshot` | Shell wrapper for agent slash command invocation (`/hermes-snapshot`) |
| `test_snapshot_compat.py` | Automated backward-compat test — ensures userend collector matches root |

## Quick Start

```bash
# 1. Install and configure
./userend/install.sh

# 2. Run from the repo root
python3 userend/collector.py

# 3. Or use the agent slash command
./userend/hermes-snapshot
./userend/hermes-snapshot dashboard
```

## Agent Integration

Register these slash commands in your Hermes Agent:

| Command | What it does |
|---------|-------------|
| `/hermes-snapshot` | Collects analytics, pushes to server, shows inline summary |
| `/hermes-snapshot dashboard` | Same as above + prints dashboard URL |

The agent simply invokes `userend/hermes-snapshot` as a shell command.
The script handles config sourcing, collection, and output formatting.

## Config File

`~/.hermes-analytics.conf` (shell-sourceable key=value format):

```bash
HERMES_ANALYTICS_USER=alice
HERMES_ANALYTICS_REMOTE=https://hermes-dash.example.com
```

## Architecture

```
YOUR MACHINE
├── ~/.hermes/                         # Hermes Agent data
│   ├── state.db
│   ├── sessions/*.jsonl
│   └── logs/agent.log
├── ~/.hermes-analytics.conf           # User config (created by install.sh)
└── hermes-analytics/                  # This repository
    └── userend/
        ├── collector.py               # The collector
        ├── install.sh                 # Setup wizard
        └── hermes-snapshot            # Agent slash command
            │
            │  POST /api/snapshots (with username)
            ▼
        SHARED SERVER
        └── server_data/
            └── alice/
                ├── snapshot_2026-06-25_091523.json
                └── snapshot_2026-06-25_145302.json
```
