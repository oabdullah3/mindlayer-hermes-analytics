## 1. Project Setup

- [ ] 1.1 Create `requirements.txt` with `flask` dependency
- [ ] 1.2 Create `server.py` with Flask app initialization and `PORT` env var support (default 5555)
- [ ] 1.3 Implement `load_snapshot()` function that reads `snapshot_latest.json` into a module-level dict

## 2. Health & Snapshot Endpoints

- [ ] 2.1 Implement `GET /api/health` — return status "ok" with `last_collection` timestamp, or 503 if no snapshot
- [ ] 2.2 Implement `GET /api/snapshots/latest` — return full loaded snapshot JSON
- [ ] 2.3 Handle missing snapshot gracefully on startup (503 with clear error, don't crash)

## 3. Skills Endpoints

- [ ] 3.1 Implement `GET /api/skills` — return `global_insights.skills` array sorted by load_count descending
- [ ] 3.2 Implement `GET /api/skills/:name` — search sessions for the named skill, return aggregated detail with per-session breakdown
- [ ] 3.3 Return 404 with `{"error": "Skill not found"}` when skill name doesn't match any session

## 4. Tools Endpoints

- [ ] 4.1 Implement `GET /api/tools` — return `global_insights.tools` array sorted by count descending
- [ ] 4.2 Implement `GET /api/tools/:name` — search sessions for the named tool, return aggregated detail
- [ ] 4.3 Return 404 with `{"error": "Tool not found"}` when tool name doesn't match any session

## 5. Sessions Endpoints

- [ ] 5.1 Implement `GET /api/sessions` — return full sessions array ordered by started_at descending
- [ ] 5.2 Implement `GET /api/sessions/:id` — return single session object by session_id
- [ ] 5.3 Return 404 with `{"error": "Session not found"}` when session ID doesn't match

## 6. Ingestion & Refresh

- [ ] 6.1 Implement `POST /api/snapshots` — accept JSON body, validate schema (sessions + global_insights required), store in memory, return 201
- [ ] 6.2 Validate Content-Type is application/json; return 400 for invalid JSON
- [ ] 6.3 Implement `POST /api/refresh` — run `subprocess.run(['python', 'collector.py'], timeout=60)`, reload snapshot on success
- [ ] 6.4 Handle collector failure: return 500 with stderr, preserve old snapshot in memory
- [ ] 6.5 Handle collector timeout: kill subprocess after 60s, return 504

## 7. Polish

- [ ] 7.1 Add JSON content-type header to all responses (`application/json`)
- [ ] 7.2 Add `pretty-print` query parameter support for indented JSON output (debug aid)
- [ ] 7.3 Print startup banner: port number, snapshot status, endpoint list to stdout

## 8. Documentation

- [ ] 8.1 Update README.md: mark REST API as ✅ in project status table, update API reference table (remove ⬜ planned markers from implemented endpoints, add confirmed response examples), add `pip install -r requirements.txt && python server.py` quick-start if not present
