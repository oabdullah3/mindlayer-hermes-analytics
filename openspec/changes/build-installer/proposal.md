## Why

The project has four components (collector, REST API, Grafana dashboards, datasources) that each require setup. Without a single install script, users must manually download Grafana, install plugins, configure datasources, provision dashboards, and install Python dependencies. `install.sh` makes this a single command. The README provides the entry point — explaining what Hermes Analytics is, how it works, and how to get started.

## What Changes

- New `install.sh` bash script that automates the full setup
- Downloads Grafana OSS v13.1.1 if not already installed
- Installs two Grafana plugins: `frser-sqlite-datasource` and `yesoreyeram-infinity-datasource`
- Copies provisioning files (dashboards + datasources) to Grafana's provisioning directory
- Configures Grafana for embedding (allow_embedding, auth.proxy in grafana.ini)
- Installs Python dependencies via `pip install -r requirements.txt`
- Runs the collector for an initial snapshot
- Idempotent — safe to run multiple times
- New `README.md` with architecture overview, installation instructions, API reference, deployment scenarios, and dashboard screenshots (placeholder)

## Capabilities

### New Capabilities

- `one-command-setup`: A single `./install.sh` script that sets up Grafana, plugins, dashboards, and Python dependencies from a fresh clone
- `project-readme`: Comprehensive README documenting architecture, installation, API endpoints, deployment scenarios, and dashboard descriptions

### Modified Capabilities

None — this is a greenfield project with no existing specs.

## Impact

- **New file:** `install.sh` (~100 lines bash)
- **New file:** `README.md` (~200 lines markdown)
- **Dependencies:** `wget`, `tar`, `pip`, Python 3
- **No code changes** — purely orchestration and documentation
