## ADDED Requirements

### Requirement: Collector resides in userend/ directory

The collector SHALL be located at `userend/collector.py` as a self-contained, installable user-side client. The directory SHALL contain all files needed for user-side operation: the collector, installer, slash-command wrapper, and compat test.

#### Scenario: User clones the repository

- **WHEN** a user clones the repository
- **THEN** `userend/collector.py` is present and runnable with `python3 userend/collector.py`

#### Scenario: Collector is importable as a Python module

- **WHEN** `userend/` is on the Python path
- **THEN** `from collector import collect, main` succeeds without import errors

### Requirement: Python is the sole implementation language

The userend client SHALL be implemented in Python 3 with no Node.js, TypeScript, or other runtime dependencies. The decision SHALL be documented with rationale in `userend/README.md` or the design doc.

#### Scenario: User asks about Node.js migration

- **WHEN** someone asks whether the collector should be ported to Node.js
- **THEN** the documented decision states Python is sufficient, citing stdlib coverage and zero native compilation needs

#### Scenario: Dependency audit

- **WHEN** reviewing `requirements.txt` for the userend client
- **THEN** the only required dependency is `flask>=3.0` (unchanged); `requests` remains optional for remote push mode

### Requirement: Root collector.py is a deprecation wrapper

The root `collector.py` SHALL be replaced with a thin wrapper that imports from `userend/collector.py`, emits a deprecation notice to stderr, and delegates all functionality.

#### Scenario: User runs root collector.py out of habit

- **WHEN** a user executes `python collector.py` at the repo root
- **THEN** the wrapper prints a deprecation notice to stderr and runs the userend collector with identical behavior

#### Scenario: Existing scripts reference root collector.py

- **WHEN** automation or cron jobs call `python /path/to/hermes-analytics/collector.py`
- **THEN** the wrapper produces the same `snapshot_latest.json` output as before

### Requirement: userend/ is a Python package

The `userend/` directory SHALL contain an `__init__.py` making it a proper Python package, enabling `from userend.collector import collect`.

#### Scenario: Import from another Python script

- **WHEN** another script does `from userend.collector import collect`
- **THEN** the import succeeds without ModuleNotFoundError

### Requirement: server.py refresh endpoint uses userend path

The `POST /api/refresh` endpoint in `server.py` SHALL invoke `userend/collector.py` instead of the root `collector.py`.

#### Scenario: Refresh via API

- **WHEN** `POST /api/refresh` is called
- **THEN** server.py runs `python3 userend/collector.py` and reloads the resulting snapshot
