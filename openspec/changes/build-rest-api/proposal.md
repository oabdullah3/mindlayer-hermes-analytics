## Why

The collector produces a snapshot JSON file, but dashboards and remote consumers need HTTP access to this data. A REST API server provides the transport layer that decouples the frontend (Grafana) from the data extraction backend. Without it, there is no way to serve analytics remotely, no way for multiple users to push snapshots, and no contract for frontend consumers.

## What Changes

- New `server.py` Flask application serving JSON-only REST API on port 5555
- No HTML templates, no Jinja, no dashboard rendering — pure JSON responses
- Endpoints: `GET /api/health`, `GET /api/snapshots/latest`, `POST /api/snapshots`, `GET /api/skills`, `GET /api/skills/:name`, `GET /api/tools`, `GET /api/tools/:name`, `GET /api/sessions`, `GET /api/sessions/:id`, `POST /api/refresh`
- Loads `snapshot_latest.json` into memory and serves structured sub-resources
- `POST /api/snapshots` accepts snapshots from remote collectors (Mode B)
- `POST /api/refresh` triggers collector re-run and returns the new snapshot
- New `requirements.txt` with `flask` dependency

## Capabilities

### New Capabilities

- `snapshot-serving`: Serve the latest snapshot and its sub-resources (skills, tools, sessions) via REST endpoints
- `remote-ingestion`: Accept snapshot POSTs from remote collector instances for multi-user/team dashboard scenarios
- `refresh-trigger`: Expose an endpoint that re-runs the collector and returns fresh data on demand

### Modified Capabilities

None — this is a greenfield project with no existing specs.

## Impact

- **New file:** `server.py` (~200 lines)
- **New file:** `requirements.txt` (flask)
- **Dependencies:** Flask, Python stdlib (json, subprocess)
- **Port:** 5555 (configurable via `PORT` env var)
- **No modifications to collector.py** — server calls collector as a subprocess
- **Frontend contract:** All Grafana dashboards and external consumers depend on this API schema
