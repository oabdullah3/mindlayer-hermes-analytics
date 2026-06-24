## Context

Hermes Agent writes structured JSON audit logs to `~/.hermes/log_payloads/YYYY-MM-DD/` for every invocation of CLI tools (currently `mindlayer-confluence-cli`, but the schema is tool-agnostic). Currently the collector does not read this directory at all — it focuses on `state.db` (SQLite) and `logs/agent.log`.

After auditing the directory (66 files, 5 days, June 10–22, 2026), the data reveals:

- **Common JSON schema per file:** `{ tool_name, command, user_email, status, started_at, finished_at, duration_ms, input_flags, result, metadata, error }`
- **100% top-level success rate** across all 66 files — but status values are arbitrary strings that can vary by tool
- **Duration range:** 10ms – 4231ms, avg 978ms
- **Flat input_flags:** All input_flags are flat key-value dicts with no nested structures
- **Workflow metadata:** 23/66 files have `metadata.workflow-id` with stages like `prepare`, `show-changes`, `finalize`
- Schema is tool-agnostic: the same top-level structure works for any CLI tool, not just Confluence

**Constraints:**

- No changes to Hermes core (external consumer only)
- Collector must handle missing/empty log_payloads gracefully (directory may not exist yet)
- Schema must anticipate future CLI tools (not just the current tool)
- Must integrate cleanly with the existing 8-step collector pipeline

## Goals / Non-Goals

**Goals:**
- Add Step 9 to collector.py: `extract_log_payloads(hermes_home) → list[dict]`
- Parse all `YYYY-MM-DD/*.json` files, extracting all common fields EXCEPT `result`
- Replace `result` with a computed `result_size` field (0 if null/empty, otherwise character count of JSON-serialized result)
- Add `log_payloads` section to the snapshot schema (top-level, alongside `sessions`): `{ operations: [...], available: bool }`

**Non-Goals:**
- Real-time streaming — batch snapshot model, same as existing collector
- Parsing non-JSON files in log_payloads — only `.json` handled
- Interpreting or storing `result` contents — result shape is tool-specific and opaque; only size is tracked
- Computing global aggregates from log_payloads — raw extraction only; downstream consumers compute aggregates as needed
- Alerting or notifications from log_payloads data in this change
- Dashboards or UI — this change is purely about data extraction into the snapshot

## Decisions

### Decision 1: Add as collector Step 9, not a separate script

**Chosen:** Extend `collector.py` with a new `extract_log_payloads()` function, called during the main snapshot generation pipeline.

**Rationale:** Single artifact output (`snapshot_latest.json`) is the core design principle. Fragmenting into multiple collector scripts duplicates error handling, remote push, and refresh logic. Keeps the one-command `python collector.py` contract intact.

**Alternatives considered:**
- Separate `log_payloads_collector.py` — rejected; duplicates push/refresh infrastructure
- Direct dashboard filesystem reads — rejected; loses remote mode (dashboard on different machine needs snapshot)

### Decision 2: Drop result, store result_size instead

**Chosen:** The `result` object is NOT stored in the snapshot. Instead, a computed `result_size` field is stored: `0` if result is `null` or `{}`, otherwise the character count of `JSON.stringify(result)`.

**Rationale:** The `result` shape varies arbitrarily by tool and command — the collector cannot know what fields are meaningful. Result objects could also be large (search results, full page content etc.) and would bloat the snapshot for data that downstream consumers may not need. `result_size` gives a quick signal: is there output? How big? Downstream consumers that need the actual result can read the original log_payloads files.

**Alternatives considered:**
- Store full result — rejected; bloats snapshot with opaque tool-specific data
- Truncate result to N chars — rejected; arbitrary cutoff loses data without solving the bloat problem

### Decision 3: No pre-computed aggregates

**Chosen:** The collector does NOT compute any global insights from log_payloads. It produces a flat `log_payloads.operations` list with raw extracted fields only. No `global_insights.log_payloads` section is added.

**Rationale:** We don't yet know what questions downstream consumers will ask of this data. Pre-computing aggregates (tool breakdown, duration stats, status distribution, workflow tracking) is premature. The snapshot already provides the raw data; consumers can compute whatever aggregates they need. This keeps the collector simple and the snapshot footprint predictable.

### Decision 4: Handle missing log_payloads gracefully

**Chosen:** If `~/.hermes/log_payloads/` doesn't exist or is empty, return an empty list and note `"log_payloads_available": false` in the snapshot. No error, no warning.

**Rationale:** Not all Hermes users will have log_payloads (it requires specific CLI tool integration). Downstream consumers handle the empty state appropriately.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| log_payloads schema drifts (new tool CLIs add fields) | Parsing is permissive — unknown top-level fields are ignored. Only known common fields are extracted |
| result_size is coarse-grained | It's a deliberate tradeoff: quick signal without storing opaque data. Consumers needing the actual result read the original files |
| File I/O for many files on every collector run | Files are tiny (avg ~2KB). Parse in a single glob+loop, no performance concern below 10K files |
| No aggregates means consumers must re-scan the snapshot | Acceptable for now. Aggregates can be added in a follow-up change once consumer needs are clear |

## Open Questions

1. Should `result_size` be byte count (UTF-8 encoded) or character count? Character count is simpler and sufficient for size estimation
2. Should we track which log_payload files have already been processed to avoid re-parsing unchanged files?
