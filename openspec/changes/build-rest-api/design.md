## Context

The collector produces `snapshot_latest.json`, but dashboards and remote consumers need HTTP access. The REST API server (`server.py`) is the transport layer — it loads the snapshot into memory and serves structured sub-resources as JSON. It's the contract between backend (collector) and frontend (Grafana).

Current state: No server exists. The plan defines a Flask-based JSON API with 10 endpoints serving skills, tools, sessions, and snapshot data.

Constraints:
- Must serve JSON only — no HTML templates, no Jinja rendering
- Must be compatible with both Mode A (local) and Mode B (remote ingest)
- Must reload snapshot data on refresh rather than keeping stale data
- Should be lightweight enough to run alongside Grafana on the same machine

## Goals / Non-Goals

**Goals:**
- Serve all snapshot data through clean, resource-oriented REST endpoints
- Accept snapshot POSTs from remote collectors for multi-user mode
- Expose a refresh endpoint that re-runs collector.py
- Return well-structured JSON with consistent field naming
- Be the single source of truth that Grafana queries

**Non-Goals:**
- Authentication or authorization — handled by Grafana's auth proxy or network-level controls
- Pagination for skills/tools lists — expected to be small enough for full-response
- Data persistence between restarts — server loads the latest snapshot; for history, the caller stores old snapshots
- HTML rendering in any form
- WebSocket or SSE for real-time updates

## Decisions

### Decision 1: Flask over FastAPI

**Chosen:** Flask for simplicity — single file, well-known, minimal boilerplate.
**Alternatives considered:**
- FastAPI: Better async support and auto-docs, but requires Pydantic and more setup. Overkill for 10 endpoints.
- http.server (stdlib): No routing, no middleware. Too primitive.

**Rationale:** Flask is a single dependency (`pip install flask`). The API is read-heavy with tiny payloads — performance is not a concern at this scale.

### Decision 2: In-memory snapshot loading at startup and on refresh

**Chosen:** Load `snapshot_latest.json` into a module-level dict at startup. Re-load on `POST /api/refresh` and `POST /api/snapshots`.
**Alternatives considered:**
- Read file on every request: Adds disk I/O to every endpoint. Slower.
- SQLite-backed: Would require schema management. The snapshot file is simpler.

**Rationale:** In-memory loading is fast (single read on startup) and the file is small (<5MB for hundreds of sessions). No cache invalidation needed beyond refresh.

### Decision 3: Port 5555 default, configurable via `PORT` env var

**Chosen:** `PORT` env var with default 5555.
**Rationale:** 5555 is unprivileged and unlikely to conflict. Grafana uses 3000 by default — they coexist.

### Decision 4: Flat endpoint structure — no version prefix

**Chosen:** `/api/skills`, `/api/tools`, `/api/sessions` — no `/api/v1/` prefix.
**Rationale:** This is an internal API consumed by known clients (Grafana datasources). Versioning adds complexity without immediate benefit. Can add `/v2/` later if needed.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Snapshot file not found on startup | Return 503 with clear error message; don't crash |
| Collector subprocess hangs on refresh | Use `subprocess.run(timeout=60)` and return 504 on timeout |
| Concurrent snapshot writes (collector + POST) | Use file locking (`fcntl`) or atomic write-then-rename in collector |
| Memory usage for very large snapshots | Load only what's needed; for 1000+ sessions, consider lazy loading or pagination |
| CORS issues for browser-based consumers | Add `flask-cors` or manual CORS headers if needed later |

## Open Questions

1. Should `GET /api/sessions` support query params for filtering (source=telegram, model=claude-3, date range)?
2. Should we add `flask-cors` by default, or leave it for users who need browser access?
3. Should `POST /api/snapshots` store old snapshots in a history directory for time-series?
