## Why

The collector currently lives at the repo root as a standalone `collector.py` — it has no install mechanism, no agent integration, and no user-side identity. ADRs 0001 and 0003 define the vision: an agent-invocable skill that users install once (`/hermes-snapshot`), configured with a username, producing snapshot JSON as the universal data contract. This change bridges the gap between the implemented collector and the accepted ADRs by restructuring it into an installable user-side client.

## What Changes

- Move `collector.py` into a new `userend/` directory as the user-side installable client
- Decision documented: **Python is sufficient** — no Node.js migration. The collector uses only stdlib (`sqlite3`, `json`, `os`, `re`, `math`) plus optional `requests`. Node.js would add native module compilation complexity (`better-sqlite3`) with zero benefit.
- Snapshot output is tested for **byte-identical compatibility** with the current collector — same schema, same data, same `snapshot_latest.json`
- Implement ADR-0001: slash commands (`/hermes-snapshot`, `/hermes-snapshot dashboard`), inline summary, `~/.hermes-analytics.conf` config
- Implement ADR-0003 verification: snapshot schema validation, backward compatibility guard
- New `userend/install.sh` (or integrated into existing install.sh) for one-command user-side setup
- Preserve existing `HERMES_ANALYTICS_REMOTE` push mode — the userend client remains a drop-in replacement

## Capabilities

### New Capabilities

- `userend-client-structure`: The collector moves to `userend/` as an installable, self-contained client. Includes the Python-sufficiency decision (no Node.js migration). Follows ADR-0001's agent-invocable skill pattern.
- `snapshot-backward-compat`: The userend client produces a snapshot identical in schema and content to the current collector. Includes automated diff testing to verify no regression.
- `agent-slash-commands`: Register `/hermes-snapshot` and `/hermes-snapshot dashboard` as agent-invocable slash commands per ADR-0001. The agent displays an inline summary after collection.
- `user-config-setup`: Install-time configuration via `~/.hermes-analytics.conf` with username prompt and optional remote server URL. Config is sourceable by both the collector and any agent skill wrapper.

### Modified Capabilities

- `remote-ingestion`: MODIFIED — `POST /api/snapshots` evolves from in-memory overwrite to per-user flat-file persistence per ADR-0002. New user-scoped endpoints added (`/api/users/*`, `/api/leaderboard/*`). Existing single-user local mode (Mode A) preserved as fallback.

## Impact

- **Moved**: `collector.py` → `userend/collector.py` (preserved with identical behavior)
- **New**: `userend/install.sh` — user-side setup script (username prompt, config, agent registration)
- **New**: `userend/test_snapshot_compat.py` — automated snapshot diff test
- **New**: `~/.hermes-analytics.conf` — per-user config file (HERMES_ANALYTICS_USER, HERMES_ANALYTICS_REMOTE)
- **Modified**: `server.py` — major rewrite: flat-file persistence replacing in-memory `_SNAPSHOT`, new user/leaderboard endpoints, `?username=` query param on existing endpoints
- **Modified**: `server.py` `/api/refresh` endpoint — updated path to userend/collector.py
- **New**: `server_data/` directory (gitignored) — per-user timestamped snapshot files
- **Dependencies**: None new in requirements.txt — Python stdlib + existing Flask
- **No changes** to extraction pipeline, snapshot schema
