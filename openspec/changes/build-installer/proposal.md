## Why

The project has three components (collector, REST API, Streamlit dashboards) that each require setup. Without a single install script, users must manually install Python dependencies, set up the userend client config, and start the server and dashboard. `install.sh` makes this a single command. The README provides the entry point — explaining what Hermes Analytics is, how it works, and how to get started.

## What Changes

- New `install.sh` bash script that automates the full setup
- Installs Python dependencies via `pip install -r requirements.txt`
- Runs `userend/install.sh` for per-user configuration (username, remote URL)
- Runs the collector for an initial snapshot
- Prints instructions to start: `python server.py &` and `streamlit run dashboard.py`
- Idempotent — safe to run multiple times
- New `README.md` with architecture overview, installation instructions, API reference, deployment scenarios, and dashboard descriptions

## Capabilities

### New Capabilities

- `one-command-setup`: A single `./install.sh` script that sets up Python dependencies, userend config, and runs the initial data collection from a fresh clone
- `project-readme`: Comprehensive README documenting architecture, installation, API endpoints, deployment scenarios, and dashboard descriptions

### Modified Capabilities

None — this is a greenfield project with no existing specs.

## Impact

- **New file:** `install.sh` (~100 lines bash)
- **New file:** `README.md` (~200 lines markdown)
- **Dependencies:** `pip`, Python 3
- **No code changes** — purely orchestration and documentation
