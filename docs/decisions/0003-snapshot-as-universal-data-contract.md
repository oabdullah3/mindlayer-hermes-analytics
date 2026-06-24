---
status: "accepted"
date: 2026-06-24
decision-makers: "oabdullah3"
---

# Snapshot JSON as the sole interchange format

## Context and Problem Statement

Hermes Analytics reads from multiple sources (`state.db`, `agent.log`, `log_payloads/`) and serves data to multiple consumers (REST API, local dashboards, remote servers). Every consumer needs the same enriched data. The question: what format should carry data between the collector and all consumers?

Constraints:
- Must be self-contained (no external database lookups needed to render a dashboard)
- Must support both local file access and HTTP transport
- Must include pre-computed aggregates so consumers don't re-derive them
- Collector is Python, consumers may be Python, JavaScript, or read-only filesystem access

## Decision

**Use a single self-contained JSON file (`snapshot_latest.json`) as the sole interchange format between the collector and all consumers.** All enrichment and aggregation happens in the collector; all consumers read the same artifact.

### Schema

```json
{
  "generated_at": "2026-06-24T09:15:23+00:00",
  "hermes_home": "/home/alice/.hermes",
  "sessions": [
    {
      "session_id": "20260624_125604_52e9b2",
      "platform": "cli",
      "chat_name": null,
      "model": "minimaxai/minimax-m2.7",
      "started_at": 1782276964.757,
      "ended_at": null,
      "ended_reason": null,
      "tokens": {
        "input": 485957,
        "output": 16316,
        "cache_read": 206608,
        "cache_write": 0,
        "reasoning": 0,
        "estimated_cost_usd": 0.0
      },
      "stats": {
        "message_count": 55,
        "tool_call_count": 31
      },
      "skills_loaded": [...],
      "tool_calls": [...],
      "shell_commands": [...],
      "user_messages": [...],
      "errors": [...]
    }
  ],
  "global_insights": {
    "total_sessions": 116,
    "total_messages": 5120,
    "total_skill_loads": 45,
    "skills": [...],
    "tools": [...],
    "commands": {
      "total_commands": 89,
      "failed_commands": 3,
      "most_executed_commands": [...],
      "failed_commands_list": [...]
    }
  }
}
```

### Design principles

1. **Collector enriches, consumers display.** All extraction, parsing, normalization, and aggregation happens in `collector.py`. Consumers (server, dashboard) never touch `state.db` or `agent.log` directly.

2. **Pre-computed aggregates.** `global_insights` contains leaderboards, totals, and breakdowns that would be expensive to re-compute on every dashboard page load.

3. **Flat session list.** Sessions are a flat array (not nested by date/user) because the snapshot represents a point-in-time state. Filtering by date or user is the consumer's responsibility.

4. **ISO 8601 UTC `generated_at`.** Every snapshot carries its own timestamp, making it self-identifying. The server uses this for history tracking.

5. **`hermes_home` tracked.** The snapshot records which Hermes data directory it came from, for debugging and multi-machine scenarios.

6. **Extensible `global_insights`.** Adding a new aggregate (e.g., `log_payloads`) adds a key to `global_insights` without breaking existing consumers.

### Transport

- **Local mode**: Written to `./snapshot_latest.json` on disk, read by `server.py` at startup
- **Remote mode**: POSTed as JSON to `{HERMES_ANALYTICS_REMOTE}/api/snapshots` with `Content-Type: application/json`

### Non-goals

- Binary format (MessagePack, protobuf) — JSON is debuggable, universal, and sufficient for snapshot sizes (~500KB for 116 sessions)
- Streaming/chunked transfer — snapshots are batch artifacts, not streams
- Schema versioning — the schema evolves additively; consumers handle missing keys gracefully

## Consequences

- Good, because one artifact serves all consumers — no format translation layer
- Good, because `cat snapshot_latest.json | jq` is a valid debugging workflow
- Good, because pre-computed aggregates make dashboard rendering fast (no per-request computation)
- Good, because HTTP POST of JSON is universally supported by servers and proxies
- Bad, because the snapshot can grow large with many sessions (mitigated: 116 sessions = ~500KB; 10,000 sessions would be ~50MB)
- Bad, because consumers must load the entire file even if they only need a subset (mitigated: REST API provides filtered sub-endpoints)

## Implementation Plan

- **Affected paths**: `collector.py` (generates the snapshot), `server.py` (reads/serves it), `snapshot_latest.json` (output artifact)
- **Dependencies**: None — `json` and `datetime` are stdlib
- **Patterns to follow**: 
  - All new collector steps add fields to the session dict in-place during the pipeline loop
  - All new global aggregates add keys to `compute_global_insights()` return dict
  - Consumers use `.get(key, default)` to handle missing keys gracefully
- **Patterns to avoid**: Nested aggregates that require recursive traversal; version prefixes in keys; binary fields

### Verification

- [ ] `python collector.py` produces a valid `snapshot_latest.json`
- [ ] `generated_at` is ISO 8601 UTC and updates on every run
- [ ] `global_insights.total_sessions` matches `len(sessions)`
- [ ] Every session has all schema keys (session_id, platform, model, tokens, stats, skills_loaded, tool_calls, shell_commands, user_messages, errors)
- [ ] Empty sessions produce empty arrays (not null or missing)
- [ ] `server.py` loads and serves the snapshot without modification
- [ ] `POST /api/snapshots` accepts the same schema the collector produces
- [ ] Adding a new key to `global_insights` does not break existing endpoints

## More Information

- This ADR documents an existing implemented pattern (collector.py has used this schema since the initial build)
- The snapshot is produced by the skill described in [ADR-0001](./0001-agent-native-skill-distribution.md)
- The multi-user server stores snapshots using this schema per [ADR-0002](./0002-push-based-multi-user-server.md)
