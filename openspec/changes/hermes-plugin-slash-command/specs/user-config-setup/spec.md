## REMOVED Requirements

### Requirement: install.sh prompts for username

**Reason**: The config wizard is replaced by environment variables. Hermes Analytics is now a Hermes plugin, and plugins use env vars (via `plugin.yaml` `requires_env` field) for configuration.

**Migration**: Set `HERMES_ANALYTICS_USER` as an environment variable. Defaults to the system username (`$USER`) if not set.

### Requirement: install.sh prompts for remote server URL

**Reason**: Same as above — interactive prompts are replaced by environment variables.

**Migration**: Set `HERMES_ANALYTICS_REMOTE` as an environment variable. The remote URL is hardcoded in production code with a default that can be overridden.

### Requirement: Config file is shell-sourceable

**Reason**: `~/.hermes-analytics.conf` is no longer created or read. Environment variables are the sole configuration mechanism.

**Migration**: Source env vars in your shell profile (`~/.bashrc`, `~/.zshrc`) or set them before running Hermes.

### Requirement: Collector includes username in remote push

**Reason**: Replaced by env-var-based username resolution.

**Migration**: Set `HERMES_ANALYTICS_USER=<your-name>` in your environment or shell profile.

### Requirement: install.sh is idempotent

**Reason**: `userend/install.sh` is removed entirely. No install script needed.

**Migration**: Plugin installation is a one-time symlink: `ln -s /path/to/repo/userend ~/.hermes/plugins/hermes-analytics`

### Requirement: install.sh registers the hermes-snapshot script

**Reason**: The standalone `hermes-snapshot` bash script is replaced by the Hermes slash command `/hermes-snapshot-analytics`.

**Migration**: Use `/hermes-snapshot-analytics` from within any Hermes chat session.

## ADDED Requirements

### Requirement: Username from environment variable

The collector SHALL read `HERMES_ANALYTICS_USER` from the environment. If not set, it SHALL fall back to the `$USER` environment variable or `os.uname().nodename`.

#### Scenario: Env var is set
- **WHEN** `HERMES_ANALYTICS_USER=alice` is in the environment
- **THEN** the collector uses `"alice"` as the username in snapshot POSTs

#### Scenario: Env var is not set
- **WHEN** `HERMES_ANALYTICS_USER` is not in the environment
- **THEN** the collector uses the value of `$USER` (or hostname as last resort)
- **AND** prints: "Username not configured. Using '<fallback>'. Set HERMES_ANALYTICS_USER to customize."

### Requirement: Remote URL from environment variable with hardcoded default

The collector SHALL use a hardcoded remote URL that can be overridden by `HERMES_ANALYTICS_REMOTE`.

#### Scenario: Env var overrides default
- **WHEN** `HERMES_ANALYTICS_REMOTE=https://custom.example.com` is set
- **THEN** the collector POSTs to `https://custom.example.com/api/snapshots`

#### Scenario: Default is used when env var is absent
- **WHEN** `HERMES_ANALYTICS_REMOTE` is not set
- **THEN** the collector uses the hardcoded production URL (if push is attempted)

### Requirement: No config file is read or written

The collector SHALL NOT read or write `~/.hermes-analytics.conf`.

#### Scenario: Old config file exists
- **WHEN** `~/.hermes-analytics.conf` exists from a previous installation
- **THEN** the collector ignores it entirely
