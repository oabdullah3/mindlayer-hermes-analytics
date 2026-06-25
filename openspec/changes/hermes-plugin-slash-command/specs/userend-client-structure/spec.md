## MODIFIED Requirements

### Requirement: userend/ is a Python package

The `userend/` directory SHALL be a Hermes plugin package containing `plugin.yaml`, `__init__.py` with `register(ctx)`, the collector, local server, and local dashboard.

#### Scenario: Import from another Python script
- **WHEN** another script does `from userend.collector import collect`
- **THEN** the import succeeds without ModuleNotFoundError

#### Scenario: Plugin is discovered by Hermes
- **WHEN** Hermes scans `~/.hermes/plugins/`
- **THEN** the `userend/` directory (via symlink) is recognized as a plugin
- **AND** `register(ctx)` is called, registering the slash command

### Requirement: Collector resides in userend/ directory

The collector SHALL be located at `userend/collector.py`. The `userend/` directory SHALL contain ALL files needed for the Hermes plugin: `plugin.yaml`, `__init__.py`, `collector.py`, `server.py` (local), and `dashboard.py` (local).

#### Scenario: Plugin directory listing
- **WHEN** listing `userend/` contents
- **THEN** the following files are present: `plugin.yaml`, `__init__.py`, `collector.py`, `server.py`, `dashboard.py`

## REMOVED Requirements

### Requirement: Python is the sole implementation language

**Reason**: This requirement is unchanged and does not need modification — Python 3 remains the sole language.

**Migration**: N/A — false removal; retained in main spec.

### Requirement: Root collector.py is a deprecation wrapper

**Reason**: The root `collector.py` may be removed or kept as a convenience shim. This is an implementation detail, not a spec-level requirement change.

**Migration**: Use `python3 userend/collector.py` or the slash command `/hermes-snapshot-analytics` instead of root `collector.py`.

### Requirement: server.py refresh endpoint uses userend path

**Reason**: The refresh endpoint is an implementation detail that depends on server location. The local server in `userend/server.py` and remote server in `remoteend/server.py` handle this differently.

**Migration**: Local server refresh imports from `userend/collector.py`; remote server refresh is triggered via client POST.

## ADDED Requirements

### Requirement: Plugin directory structure

The `userend/` directory SHALL follow the Hermes plugin structure with `plugin.yaml` manifest and `__init__.py` registration module.

#### Scenario: Plugin manifest is present
- **WHEN** Hermes scans the plugin directory
- **THEN** `plugin.yaml` is found with `name: hermes-analytics`, `version`, and `provides_commands`

#### Scenario: Registration function is present
- **WHEN** Hermes loads the plugin
- **THEN** `__init__.py` exports a `register(ctx)` function that registers `/hermes-snapshot-analytics`

### Requirement: Local server and dashboard are bundled in userend

The `userend/` directory SHALL include `server.py` (single-user local Flask server) and `dashboard.py` (single-user local Streamlit dashboard).

#### Scenario: Local server is startable
- **WHEN** the slash command handler spawns `python3 userend/server.py`
- **THEN** the server starts on the configured port and serves the latest snapshot

#### Scenario: Local dashboard is startable
- **WHEN** the slash command handler spawns `streamlit run userend/dashboard.py`
- **THEN** the dashboard starts on the configured port and displays analytics from the local server
