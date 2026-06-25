## ADDED Requirements

### Requirement: Plugin manifest file

The `userend/` directory SHALL contain a `plugin.yaml` manifest declaring the plugin metadata, provided slash commands, and required environment variables.

#### Scenario: Manifest declares plugin identity
- **WHEN** Hermes scans `~/.hermes/plugins/`
- **THEN** the manifest provides `name: hermes-analytics`, `version`, and `description` fields
- **AND** `provides_commands` lists `hermes-snapshot-analytics`

#### Scenario: Manifest declares required environment variables
- **WHEN** `HERMES_ANALYTICS_REMOTE` is not set
- **THEN** the plugin remains enabled (remote URL is optional, not required)
- **AND** the slash command still works in local-only mode

### Requirement: Plugin registration module

`userend/__init__.py` SHALL contain a `register(ctx)` function that registers the `/hermes-snapshot-analytics` slash command with Hermes.

#### Scenario: Plugin loads successfully
- **WHEN** Hermes starts and discovers the plugin
- **THEN** `register(ctx)` is called exactly once
- **AND** the slash command `/hermes-snapshot-analytics` is available in CLI and gateway sessions

#### Scenario: Plugin appears in /plugins list
- **WHEN** a user types `/plugins` in a Hermes session
- **THEN** `hermes-analytics` appears with its version and slash command count

#### Scenario: Slash command appears in /help
- **WHEN** a user types `/help` in a Hermes session
- **THEN** `/hermes-snapshot-analytics` appears in the slash command list with its description

### Requirement: Plugin is symlink-installed

The plugin SHALL be installed by creating a symlink from `~/.hermes/plugins/hermes-analytics` to the repo's `userend/` directory.

#### Scenario: First-time setup
- **WHEN** a user runs the setup step `ln -s /path/to/repo/userend ~/.hermes/plugins/hermes-analytics`
- **THEN** Hermes discovers the plugin on next startup
- **AND** the plugin manifest and `__init__.py` are found at the symlink target

#### Scenario: Symlink already exists
- **WHEN** the symlink `~/.hermes/plugins/hermes-analytics` already points to `userend/`
- **THEN** no action is needed and the plugin continues to work

### Requirement: Plugin is self-contained

All plugin code, the collector, local server, and local dashboard SHALL reside within `userend/` or be importable from it.

#### Scenario: Plugin directory contains all needed files
- **WHEN** listing `userend/` contents
- **THEN** `plugin.yaml`, `__init__.py`, `collector.py`, `server.py`, and `dashboard.py` are all present
