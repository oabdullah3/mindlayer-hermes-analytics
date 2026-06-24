## ADDED Requirements

### Requirement: install.sh downloads Grafana OSS

The install script SHALL download Grafana OSS v13.1.1 for Linux x86_64 from the official Grafana CDN if `./grafana-server` binary does not already exist.

#### Scenario: Grafana not installed

- **WHEN** `./grafana-server/grafana-server` does not exist
- **THEN** the script downloads `grafana-13.1.1.linux-amd64.tar.gz`, extracts it, and the binary is available at `./grafana-server/grafana-server`

#### Scenario: Grafana already installed

- **WHEN** `./grafana-server/grafana-server` already exists
- **THEN** the script prints "Grafana already installed" and skips the download step

#### Scenario: wget not available

- **WHEN** `wget` is not found on the system
- **THEN** the script prints "Error: wget is required. Install it first." and exits with code 1

### Requirement: install.sh installs Grafana plugins

The install script SHALL install the `frser-sqlite-datasource` and `yesoreyeram-infinity-datasource` plugins using `grafana-cli` if they are not already installed.

#### Scenario: Plugins not installed

- **WHEN** plugins are not present in Grafana's plugin directory
- **THEN** the script runs `grafana-cli plugins install <plugin>` for each plugin

#### Scenario: Plugins already installed

- **WHEN** plugins are already present
- **THEN** the script prints "Plugin already installed: <name>" and skips that plugin

### Requirement: install.sh copies provisioning files

The install script SHALL copy all files from `grafana/provisioning/dashboards/` and `grafana/provisioning/datasources/` to Grafana's provisioning directory (`conf/provisioning/`).

#### Scenario: Provisioning source exists

- **WHEN** `grafana/provisioning/` contains dashboard JSONs and datasource YAMLs
- **THEN** the script copies them to `grafana-server/conf/provisioning/` preserving the directory structure

#### Scenario: Provisioning source missing

- **WHEN** `grafana/provisioning/` does not exist
- **THEN** the script prints a warning and skips the copy step

### Requirement: install.sh configures Grafana for embedding

The install script SHALL configure `grafana.ini` with `allow_embedding = true` and `[auth.proxy]` settings for iframe embedding support.

#### Scenario: grafana.ini exists

- **WHEN** `grafana-server/conf/grafana.ini` (or `defaults.ini`) exists
- **THEN** the script appends or uncomments `allow_embedding = true` in the `[security]` section

#### Scenario: grafana.ini does not exist

- **WHEN** Grafana's config file is not at the expected path
- **THEN** the script prints a warning and continues

### Requirement: install.sh installs Python dependencies

The install script SHALL run `pip install -r requirements.txt` to install Flask.

#### Scenario: pip available

- **WHEN** pip (or pip3) is found and requirements.txt exists
- **THEN** Python dependencies are installed

#### Scenario: pip not available

- **WHEN** neither pip nor pip3 is found
- **THEN** the script prints "Error: pip is required. Install Python 3 and pip first." and exits

### Requirement: install.sh runs initial collector

The install script SHALL run `python3 collector.py` to generate the initial `snapshot_latest.json`.

#### Scenario: collector.py exists

- **WHEN** `collector.py` is present and state.db is accessible
- **THEN** the script runs the collector and prints the summary (session count, skill count, output path)

#### Scenario: collector fails

- **WHEN** the collector exits with an error
- **THEN** the script prints the error but does not abort — the user can run it manually later

### Requirement: install.sh is idempotent

The install script SHALL be safe to run multiple times without corrupting existing configurations or duplicating setup steps.

#### Scenario: Re-run after successful install

- **WHEN** install.sh is run a second time after a successful first run
- **THEN** each step detects the existing state and skips or reports "already done"
