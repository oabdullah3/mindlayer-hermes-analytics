---
status: "accepted"
date: 2026-06-24
decision-makers: "oabdullah3"
---

# Distribute Hermes Analytics as an agent-invocable skill

## Context and Problem Statement

Hermes Analytics is currently a standalone CLI tool (`python collector.py`) and a Flask server (`server.py`). Users must context-switch to a terminal, run commands, and remember they have analytics at all. The tool should be available from within the Hermes agent itself — invoked via slash commands or triggered automatically when the agent detects analytics-relevant context.

The key question: how should users install and interact with Hermes Analytics from within their agent?

Constraints:
- Must work as a skill inside Hermes-like agents (no changes to agent core)
- User identity must be established at install time (needed for multi-user server)
- Two tiers of interaction: lightweight inline summary, and full localhost dashboard
- Dashboard technology is explicitly excluded from this ADR (separate decision pending)

## Decision

**Distribute Hermes Analytics as an installable skill** with an interactive installer that prompts for a username, configures the environment, and registers two slash commands.

### Slash commands

| Command | Collects | Pushes to remote | Shows inline summary | Starts local dashboard |
|---|---|---|---|---|
| `/hermes-snapshot` | ✅ | ✅ | ✅ | ❌ |
| `/hermes-snapshot dashboard` | ✅ | ✅ | ✅ | ✅ |

### Auto-detection

The agent MAY detect analytics-relevant context (e.g., user asks "how many skills have I loaded recently?") and offer to run `/hermes-snapshot`. The user can accept or decline. This is a UX enhancement, not a hard requirement.

### Install flow

1. User runs the installer (e.g., `./install.sh` or a skill marketplace install)
2. Installer prompts: `Enter your username for Hermes Analytics:`
3. Username is written to `~/.hermes-analytics.conf` as `HERMES_ANALYTICS_USER=...`
4. Installer registers the two slash commands with the agent's skill registry
5. If remote server URL is known, optionally prompt: `Analytics server URL? [skip for local-only]` → stored as `HERMES_ANALYTICS_REMOTE`

### Inline summary

After a successful `/hermes-snapshot`, the agent displays a compact summary in the chat:
```
📊 Hermes Analytics Snapshot
   Sessions: 116
   Skills loaded: 45 (top: confluence-skill ×12)
   Tool calls: 320 across 18 tools
   Shell commands: 89 (3 failed)
   Errors: 2
   Pushed to: https://hermes-dash.example.com ✅
```

### Non-goals

- Dashboard technology choice (Streamlit, Plotly Dash, etc.) — separate ADR
- Real-time streaming — snapshots are batch, not streaming
- Agent auto-triggering without user consent — always offers, never runs silently

## Consequences

- Good, because users never leave their agent to get analytics
- Good, because install-time username setup avoids runtime confusion
- Good, because two-tier commands (summary vs dashboard) lets users choose depth
- Good, because `~/.hermes-analytics.conf` is a clean single-file config
- Bad, because requires agent platform support for custom slash commands (depends on Hermes agent's skill system)
- Bad, because installer must detect agent type to register commands correctly

## Implementation Plan

- **Affected paths**: New: `install.sh` (or `install.py`), `~/.hermes-analytics.conf`, skill manifest file (format TBD based on agent platform)
- **Dependencies**: None new in `requirements.txt` — installer uses `python3` stdlib only
- **Patterns to follow**: `collector.py` already reads `HERMES_ANALYTICS_REMOTE` from env; add `HERMES_ANALYTICS_USER` reading in the same pattern
- **Patterns to avoid**: Hardcoding paths; assuming agent platform details in ADR (those go in the skill manifest)

### Verification

- [ ] Running `./install.sh` prompts for username and writes `~/.hermes-analytics.conf`
- [ ] `/hermes-snapshot` runs collector, pushes to remote, and displays inline summary
- [ ] `/hermes-snapshot dashboard` does all of the above AND starts a local dashboard server
- [ ] When `HERMES_ANALYTICS_REMOTE` is unset, summary shows "Saved locally" instead of "Pushed to..."
- [ ] `~/.hermes-analytics.conf` is source-able by `collector.py` (env var format)
- [ ] Installer is idempotent — running it again updates config, doesn't break

## Alternatives Considered

- **MCP server instead of skill**: Rejected — MCP requires a separate server process and connection setup; a skill integrates directly with the agent's command lifecycle
- **Auto-detect username from `$USER`/git**: Rejected — `$USER` is unreliable across systems, and the user may want a different display name on the server
- **Runtime username prompt on every snapshot**: Rejected — annoying friction; install-time setup is one-and-done

## More Information

- The username configured by this ADR is consumed by the multi-user server described in [ADR-0002](./0002-push-based-multi-user-server.md)
- The snapshot produced by `/hermes-snapshot` follows the schema defined in [ADR-0003](./0003-snapshot-as-universal-data-contract.md)
