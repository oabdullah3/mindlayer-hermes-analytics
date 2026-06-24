## Context

The Hermes Analytics platform needs a data extraction layer that reads from Hermes Agent's local files (~/.hermes/) and produces a structured JSON snapshot. This collector is the first component in the pipeline — the REST API and Grafana dashboards both depend on its output. The collector must work without modifying Hermes core code.

Current state: No collector exists. Hermes writes to state.db, sessions/*.jsonl, logs/agent.log, and log_payloads/*.json but nothing aggregates or enriches this data for analytics purposes.

Constraints:
- Must be Python 3 (consistent with Hermes ecosystem)
- Must tolerate missing data sources gracefully (log_payloads and .skills_prompt_snapshot.json may not exist)
- Must be fast enough for cron-based re-runs (target: <5s for 100 sessions)
- Must not lock state.db while Hermes is writing

## Goals / Non-Goals

**Goals:**
- Extract all skill loads, tool calls, errors, and session metadata from Hermes data sources
- Produce a self-contained `snapshot_latest.json` that downstream consumers can read without accessing Hermes files
- Enrich raw data with derived metrics: token estimates per skill, error-to-duration mapping, preceding user messages for skill loads
- Support optional remote push for multi-user/team dashboard scenarios
- Be invocable manually (`python collector.py`), via cron, or programmatically (importable module)

**Non-Goals:**
- Real-time streaming — snapshot approach with periodic re-runs is sufficient
- Per-message token counting — state.db has the column but Hermes doesn't populate it
- Auto-load vs manual skill detection — can infer heuristically but Hermes doesn't expose this distinction
- Modifying Hermes core code — entirely external consumer
- Writing to a database — the REST API server handles persistence; collector produces a JSON file

## Decisions

### Decision 1: JSON snapshot over database writes

**Chosen:** Collector writes `snapshot_latest.json` to disk and optionally POSTs to a remote API.
**Alternatives considered:**
- Direct SQLite writes: Would couple collector to a specific storage schema. JSON is universal.
- Direct REST API dependency: Collector shouldn't require a running server. Mode A needs zero network.

**Rationale:** JSON file is the simplest artifact that any downstream consumer (Python, Grafana, shell scripts) can read. The server.py can load it into memory and serve it.

### Decision 2: Single `collector.py` over multi-file package

**Chosen:** One Python file with ~300-400 lines and clear step functions.
**Alternatives considered:**
- Multi-file package (collector/sessions.py, collector/skills.py, etc.): Overkill for this size.
- Config-driven extraction: Adds complexity without benefit at this scale.

**Rationale:** Single file is easy to audit, ship, and run. The 7-step pipeline maps cleanly to 7 functions.

### Decision 3: `requests` as optional import for remote push only

**Chosen:** Import `requests` only when `HERMES_ANALYTICS_REMOTE` is set. Standard library for everything else.
**Rationale:** Keeps zero dependencies for local-only users. Mode A users don't need to install anything beyond Python 3.

### Decision 4: `HERMES_HOME` env var with `~/.hermes` default

**Chosen:** Respect `HERMES_HOME` environment variable, falling back to `~/.hermes`.
**Rationale:** Some users have non-standard Hermes install locations. Most will use the default.

### Decision 5: Gracious failure on missing optional sources

**Chosen:** If `log_payloads/` or `.skills_prompt_snapshot.json` don't exist, skip those enrichments and log a warning. Missing `state.db` is a fatal error.
**Rationale:** Not all Hermes deployments produce all data sources. The collector should work with whatever is available.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Snapshot becomes stale between collector runs | Cron-based refresh (every 15min) or `/api/refresh` trigger. Grafana polls every 5min by default. |
| Large state.db (1000+ sessions) may cause slow queries | Use indexed columns in SQL queries. Target <5s for typical usage. |
| SQLite lock contention if Hermes writes during collector read | SQLite supports concurrent reads. Collector only SELECTs — never writes to state.db. |
| JSONL files may be partially written during collection | Open files in read-only mode. Gracefully skip truncated last lines. |
| Remote POST fails (network down, server unreachable) | Log the error, write locally as fallback. Don't lose data. |

## Open Questions

1. Should the collector cache parsed results to avoid re-parsing JSONL on every run? (Could use a SQLite cache DB — adds complexity, may not be needed if runs are fast enough.)
2. Should we support incremental collection (only new sessions since last run) or always full-scan? (Full-scan is simpler; incremental adds timestamp-tracking complexity.)
3. Should skill auto-load inference use simple heuristics (user message mentions skill name?) or skip this entirely?
