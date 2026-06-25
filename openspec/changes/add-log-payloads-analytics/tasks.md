## 1. Collector — Log Payloads Extraction (Step 9)

- [x] 1.1 Add `extract_log_payloads(hermes_home: str) -> list[dict]` function to collector.py that globs `{hermes_home}/log_payloads/**/*.json` and parses each file
- [x] 1.2 Implement common schema extraction: extract `tool_name`, `command`, `user_email`, `status`, `started_at`, `finished_at`, `duration_ms`, `input_flags`, `metadata`, `error` from each payload; drop `result`; compute and store `result_size` (0 if null/`{}`, otherwise `len(json.dumps(result))`)
- [x] 1.3 Track `source_file` for each operation: the relative path under `log_payloads/`
- [x] 1.4 Handle malformed JSON: catch `JSONDecodeError`, log WARNING with filename, skip file
- [x] 1.5 Handle missing directory: if `log_payloads/` doesn't exist, return empty list, set `log_payloads_available: false`

## 2. Snapshot Schema Integration

- [x] 2.1 Add `log_payloads` top-level key to snapshot JSON: `{ operations: [...], available: bool }`
- [x] 2.2 Call `extract_log_payloads()` as Step 9 in the main collector pipeline, after Step 8 (errors)
- [x] 2.3 Update `collector.py` main() to include log_payloads data in the final `generate_snapshot()` call

## 3. Integration & Validation

- [x] 3.1 Run `python collector.py` and verify `snapshot_latest.json` contains new `log_payloads` key with `operations` and `available` fields
- [x] 3.2 Verify each operation has all expected fields (tool_name, command, user_email, status, started_at, finished_at, duration_ms, input_flags, metadata, error, result_size, source_file) and that `result` is NOT present
- [x] 3.3 Verify graceful handling: rename `log_payloads/` to test empty-state behavior, create a malformed JSON file to test error skipping
- [x] 3.4 Update README.md: add `log_payloads` to collector pipeline table as Step 9
