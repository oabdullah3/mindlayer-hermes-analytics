## ADDED Requirements

### Requirement: Payload file discovery

The collector SHALL discover all JSON payload files under `~/.hermes/log_payloads/` organized by date subdirectories (`YYYY-MM-DD/*.json`).

#### Scenario: log_payloads directory exists with files

- **WHEN** `~/.hermes/log_payloads/` contains date subdirectories with `.json` files
- **THEN** the collector discovers and parses every `.json` file across all subdirectories

#### Scenario: log_payloads directory does not exist

- **WHEN** `~/.hermes/log_payloads/` does not exist or is empty
- **THEN** the collector returns an empty operations list and sets `log_payloads_available: false` in the snapshot without raising an error

#### Scenario: Non-JSON files present in log_payloads

- **WHEN** the directory contains files without `.json` extension (e.g., `.log`, `.tmp`)
- **THEN** those files SHALL be silently skipped

### Requirement: Common schema extraction

Every JSON payload file follows a consistent top-level schema regardless of the tool or command. The collector SHALL extract all fields EXCEPT `result`, and SHALL replace `result` with a computed `result_size` field.

**Fields extracted into each operation:**

| Field | Source | Notes |
|-------|--------|-------|
| `tool_name` | payload | Identifies which CLI tool produced the payload |
| `command` | payload | The operation invoked within the tool |
| `user_email` | payload | The user who executed the command |
| `status` | payload | Outcome — an arbitrary string, not limited to a fixed set |
| `started_at` | payload | ISO 8601 — when the command began |
| `finished_at` | payload | ISO 8601 — when the command completed |
| `duration_ms` | payload | Elapsed time in milliseconds |
| `input_flags` | payload | Always a flat key-value dict. May be empty `{}` |
| `metadata` | payload | May be empty `{}`. If non-empty, contains `workflow-id` and `stage` |
| `error` | payload | Error message if the command failed, `null` otherwise |
| `result_size` | **computed** | Size of the `result` object: `0` if result is `null` or `{}`, otherwise the character count of `JSON.stringify(result)`. The `result` object itself is NOT stored in the snapshot |
| `source_file` | **computed** | Relative path of the source JSON file under `log_payloads/` |

#### Scenario: Well-formed JSON payload

- **WHEN** a payload file contains valid JSON matching the top-level schema
- **THEN** the collector extracts all fields into the operations list, drops `result`, and stores `result_size` computed from the original `result`

#### Scenario: Result is null or empty

- **WHEN** a payload has `"result": null` or `"result": {}`
- **THEN** `result_size` is `0`

#### Scenario: Result has content

- **WHEN** a payload has a non-empty `result` object
- **THEN** `result_size` is the character count of the JSON-serialized result

#### Scenario: Input flags are empty

- **WHEN** a payload has `input_flags: {}`
- **THEN** the collector stores `input_flags: {}` — empty flags are valid

#### Scenario: Metadata is empty (no workflow)

- **WHEN** a payload has `metadata: {}`
- **THEN** the collector stores `metadata: {}` — this operation is not part of a multi-step workflow

#### Scenario: Metadata contains workflow-id and stage

- **WHEN** a payload has `metadata: {"workflow-id": "abc-123", "stage": "prepare"}`
- **THEN** the collector preserves both fields as-is within `metadata`

#### Scenario: Malformed JSON payload

- **WHEN** a payload file contains invalid or unparseable JSON
- **THEN** the collector logs a WARNING with the filename and skips that file

#### Scenario: Missing optional fields

- **WHEN** a payload is missing `user_email`, `metadata`, or `error`
- **THEN** the collector uses `null` for those fields and continues processing

#### Scenario: Unknown tool or command

- **WHEN** a payload has a `tool_name` or `command` value never seen before
- **THEN** the collector stores it as-is — no tool or command is treated as an error

### Requirement: Snapshot schema integration

The collector SHALL include the log payloads data in the snapshot under a top-level `log_payloads` key.

#### Scenario: Snapshot generated with log payload data

- **WHEN** the collector runs successfully
- **THEN** `snapshot_latest.json` contains:
  - `log_payloads.operations` — flat list of all parsed operations with all fields from the schema table above
  - `log_payloads.available` — boolean (`true`)

#### Scenario: Snapshot generated without log payload data

- **WHEN** `log_payloads/` directory does not exist or is empty
- **THEN** `log_payloads.available` is `false` and `log_payloads.operations` is `[]`
