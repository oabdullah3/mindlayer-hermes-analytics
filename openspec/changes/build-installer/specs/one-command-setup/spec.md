## ADDED Requirements

### Requirement: install.sh installs Python dependencies

The install script SHALL run `pip install -r requirements.txt` to install Flask, Streamlit, and Plotly.

#### Scenario: pip available

- **WHEN** pip (or pip3) is found and requirements.txt exists
- **THEN** Python dependencies are installed

#### Scenario: pip not available

- **WHEN** neither pip nor pip3 is found
- **THEN** the script prints "Error: pip is required. Install Python 3 and pip first." and exits

#### Scenario: Dependencies already installed

- **WHEN** all required packages (flask, streamlit, plotly) are already importable
- **THEN** the script prints "Python dependencies already installed" and skips pip install

### Requirement: install.sh configures userend client

The install script SHALL run `userend/install.sh` to prompt for username and remote server URL, writing to `~/.hermes-analytics.conf`.

#### Scenario: userend/install.sh exists

- **WHEN** `userend/install.sh` is present and executable
- **THEN** the script runs it to configure the userend client

#### Scenario: Config already exists

- **WHEN** `~/.hermes-analytics.conf` already exists
- **THEN** the script prints "Hermes Analytics already configured for: <username>" and skips userend setup

#### Scenario: userend/install.sh not found

- **WHEN** `userend/install.sh` does not exist
- **THEN** the script prints a warning and skips user configuration

### Requirement: install.sh runs initial collector

The install script SHALL run `python3 collector.py` to generate the initial `snapshot_latest.json`.

#### Scenario: collector.py exists

- **WHEN** `collector.py` is present and state.db is accessible
- **THEN** the script runs the collector and prints the summary (session count, skill count, output path)

#### Scenario: collector fails

- **WHEN** the collector exits with an error
- **THEN** the script prints the error but does not abort — the user can run it manually later

### Requirement: install.sh prints start instructions

The install script SHALL print clear instructions to start the server, dashboard, and where to open the browser.

#### Scenario: Successful install

- **WHEN** install.sh completes all steps successfully
- **THEN** the script prints:
  - "Start server: python server.py &"
  - "Start dashboard: streamlit run dashboard.py"
  - "Open: http://localhost:8501"

### Requirement: install.sh is idempotent

The install script SHALL be safe to run multiple times without corrupting existing configurations or duplicating setup steps.

#### Scenario: Re-run after successful install

- **WHEN** install.sh is run a second time after a successful first run
- **THEN** each step detects the existing state and skips or reports "already done"
