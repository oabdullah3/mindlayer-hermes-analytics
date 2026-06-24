## ADDED Requirements

### Requirement: README includes project overview

The README SHALL include a project title, one-line description ("External analytics dashboard for Hermes Agent — track skill usage, tool calls, and session costs"), and key selling points (zero Hermes modifications, Grafana-powered, remote-deployable).

#### Scenario: Reader lands on repo

- **WHEN** someone visits the repository or opens README.md
- **THEN** the first section clearly explains what Hermes Analytics is and why it exists

### Requirement: README includes ASCII architecture diagram

The README SHALL include an ASCII architecture diagram showing the data flow: Hermes files → collector → snapshot → REST API → Grafana dashboards, with Mode A (local) and Mode B (remote) labeled.

#### Scenario: Understanding the system

- **WHEN** a developer wants to understand how components interact
- **THEN** the ASCII diagram provides a clear visual overview

### Requirement: README includes installation instructions

The README SHALL document both setup modes:
- **Local (Mode A):** clone → `./install.sh` → `python server.py &` → `./grafana-server` → open localhost:3000
- **Remote (Mode B):** steps for remote server setup + per-machine collector config with `HERMES_ANALYTICS_REMOTE`

#### Scenario: New user setting up the project

- **WHEN** a user follows the installation section
- **THEN** they have a working system at the end

### Requirement: README includes API reference

The README SHALL list all REST API endpoints with method, path, description, and example response (truncated).

#### Scenario: Developer integrating with the API

- **WHEN** someone needs to query analytics programmatically
- **THEN** the API reference provides all endpoints and their response shapes

### Requirement: README documents all 4 dashboards

The README SHALL describe each of the 4 dashboards with their purpose and a list of panels, marking the two primary USP dashboards (skills, tools) with ⭐.

#### Scenario: User exploring available dashboards

- **WHEN** Grafana is running and dashboards are provisioned
- **THEN** the README tells the user what each dashboard shows

### Requirement: README includes deployment scenarios table

The README SHALL include a table showing 4 deployment scenarios: Dev/Single User, Team Dashboard, Cloud Dashboard, Embedded.

#### Scenario: User planning production deployment

- **WHEN** someone needs to decide how to deploy
- **THEN** the deployment table provides clear options with trade-offs

### Requirement: README includes open questions / future roadmap

The README SHALL list known limitations and future directions (per-message tokens, auto-load detection, real-time updates, multi-tenancy) as documented in PLAN.md.

#### Scenario: Contributor wants to know what's next

- **WHEN** someone wants to contribute or understand roadmap
- **THEN** the open questions section provides clear direction
