## ADDED Requirements

### Requirement: install.sh prompts for username

The userend installer (`userend/install.sh`) SHALL prompt the user for a username on first run and write it to `~/.hermes-analytics.conf`.

#### Scenario: First-time install

- **WHEN** `userend/install.sh` is run and `~/.hermes-analytics.conf` does not exist
- **THEN** the script prompts: "Enter your username for Hermes Analytics:"
- **AND** writes `HERMES_ANALYTICS_USER=<input>` to `~/.hermes-analytics.conf`

#### Scenario: Re-run preserves existing config

- **WHEN** `userend/install.sh` is run and `~/.hermes-analytics.conf` already exists
- **THEN** the script reads the existing username, prints "Already configured as: <username>", and does NOT overwrite unless the user confirms

### Requirement: install.sh prompts for remote server URL

The userend installer SHALL optionally prompt for a remote analytics server URL and write it to `~/.hermes-analytics.conf`.

#### Scenario: User provides remote URL

- **WHEN** the installer asks "Analytics server URL? [skip for local-only]:"
- **AND** the user enters a URL like `https://hermes-dash.example.com`
- **THEN** `HERMES_ANALYTICS_REMOTE=https://hermes-dash.example.com` is written to the config file

#### Scenario: User skips remote URL

- **WHEN** the installer asks for the server URL and the user presses Enter (empty input)
- **THEN** no `HERMES_ANALYTICS_REMOTE` line is written and the collector operates in local-only mode

### Requirement: Config file is shell-sourceable

`~/.hermes-analytics.conf` SHALL use `KEY=value` format (one per line) that can be sourced by both bash scripts and parsed by Python.

#### Scenario: Bash sources the config

- **WHEN** a script runs `source ~/.hermes-analytics.conf`
- **THEN** `$HERMES_ANALYTICS_USER` and `$HERMES_ANALYTICS_REMOTE` (if set) are available as environment variables

#### Scenario: Python reads the config

- **WHEN** the collector initializes and `~/.hermes-analytics.conf` exists
- **THEN** the collector reads `HERMES_ANALYTICS_USER` and `HERMES_ANALYTICS_REMOTE` from the file and makes them available

### Requirement: Collector includes username in remote push

When `HERMES_ANALYTICS_REMOTE` is set, the collector SHALL include the configured username in the POST body alongside `sessions` and `global_insights`.

#### Scenario: Remote push with username

- **WHEN** the collector POSTs to the remote server
- **AND** `HERMES_ANALYTICS_USER=alice` is configured
- **THEN** the JSON body includes `"username": "alice"` at the top level

#### Scenario: Remote push without username configured

- **WHEN** the collector POSTs to the remote server
- **AND** `HERMES_ANALYTICS_USER` is not configured
- **THEN** the collector prints a warning and proceeds without a username field (server may reject or treat as anonymous)

### Requirement: install.sh is idempotent

The userend installer SHALL be safe to run multiple times without duplicating config entries or breaking existing setup.

#### Scenario: Re-run after successful install

- **WHEN** `userend/install.sh` is run a second time
- **THEN** it detects the existing config and reports current settings without prompting again (unless `--reconfigure` flag is passed)

### Requirement: install.sh registers the hermes-snapshot script

The userend installer SHALL make `userend/hermes-snapshot` executable (`chmod +x`) and verify it is invocable.

#### Scenario: Post-install verification

- **WHEN** install.sh completes successfully
- **THEN** `userend/hermes-snapshot` has execute permissions
- **AND** the installer prints: "Run `/hermes-snapshot` from your agent to collect analytics"
