## ADDED Requirements

### Requirement: Snapshot output is identical to current collector

The userend collector SHALL produce a `snapshot_latest.json` that is semantically identical to the one produced by the current root `collector.py`. All fields, values, arrays, and nested objects MUST match exactly, with the exception of `generated_at` (which varies per run).

#### Scenario: Same hermes_home produces identical output

- **WHEN** both the old root collector and the new userend collector are run against the same `HERMES_HOME`
- **THEN** the resulting JSON trees are identical after normalizing `generated_at`

#### Scenario: Snapshot schema is unchanged

- **WHEN** the userend collector generates a snapshot
- **THEN** the top-level keys are exactly `generated_at`, `hermes_home`, `sessions`, `global_insights`
- **AND** every session has exactly the keys: `session_id`, `platform`, `chat_name`, `model`, `started_at`, `ended_at`, `ended_reason`, `tokens`, `stats`, `skills_loaded`, `tool_calls`, `shell_commands`, `user_messages`, `errors`

### Requirement: Automated compat test exists

An automated test script SHALL exist at `userend/test_snapshot_compat.py` that runs both collectors, normalizes timestamps, and deep-compares the resulting JSON.

#### Scenario: Test passes on identical output

- **WHEN** `python3 userend/test_snapshot_compat.py` is run
- **AND** both collectors produce semantically identical snapshots
- **THEN** the script exits with code 0 and prints "PASS: Snapshots are identical"

#### Scenario: Test fails on divergent output

- **WHEN** the userend collector produces a snapshot that differs from the root collector (excluding `generated_at`)
- **THEN** the script exits with code 1 and prints the specific diff (key path, expected value, actual value)

#### Scenario: Test normalizes generated_at

- **WHEN** comparing two snapshots with different `generated_at` values
- **THEN** the `generated_at` field is ignored during comparison

### Requirement: Remote push produces identical POST body

When `HERMES_ANALYTICS_REMOTE` is set, the userend collector SHALL POST the same JSON body (same keys, same values, same structure) as the root collector.

#### Scenario: Remote push payload matches

- **WHEN** both collectors are run with `HERMES_ANALYTICS_REMOTE=https://example.com`
- **THEN** the JSON body POSTed to `/api/snapshots` is identical (excluding `generated_at`)

### Requirement: Command-line interface is unchanged

The userend collector SHALL support the same CLI arguments (`--hermes-home`, `--output`) and environment variables (`HERMES_HOME`, `HERMES_ANALYTICS_REMOTE`) as the root collector.

#### Scenario: CLI arguments work identically

- **WHEN** `python3 userend/collector.py --hermes-home /custom/path --output custom.json` is run
- **THEN** the snapshot is written to `custom.json` using data from `/custom/path`
