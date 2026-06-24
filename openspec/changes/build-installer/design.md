## Context

The project consists of four independently-built components (collector, REST API, Grafana dashboards, datasources) that must work together. A user cloning the repo faces several manual steps: download Grafana, install plugins, configure datasources, copy dashboards, install Python deps, run an initial collection. `install.sh` collapses this into one command. `README.md` is the project's front door.

Current state: No installer or README exists. The repository contains only PLAN.md and the openspec scaffolding.

Constraints:
- Must work on Linux (x86_64) — Grafana OSS binary target
- Must be idempotent (safe to run `./install.sh` multiple times)
- Must handle the case where Grafana is already installed (skip download)
- Must not require root privileges (Grafana runs as a regular user)

## Goals / Non-Goals

**Goals:**
- Single command setup: `./install.sh` from a fresh clone to a working system
- Idempotent: safe to re-run without breaking existing configs
- Clear progress output: each step prints what it's doing
- Error handling: detect failures (missing wget, pip, etc.) and exit with clear messages
- README covers: project overview, architecture diagram (ASCII), installation, API reference, dashboard descriptions, deployment scenarios

**Non-Goals:**
- macOS or Windows support (Linux only initially)
- Docker-based setup (can add later)
- Systemd service files for Grafana/server.py (manual start is fine for v1)
- Uninstall script
- Package manager integration (apt, brew)

## Decisions

### Decision 1: Bash over Python for install script

**Chosen:** Plain bash script — no Python dependency for installation itself.
**Rationale:** The install script installs Python dependencies. Using Python for the installer creates a chicken-and-egg problem. Bash is universally available on Linux.

### Decision 2: Download Grafana locally, not system-wide

**Chosen:** Download and extract Grafana into `./grafana-server/` within the project directory. No system-wide installation.
**Rationale:** No root required. Easy cleanup (`rm -rf grafana-server/`). Works for development and single-user deployment.

### Decision 3: README as single comprehensive document

**Chosen:** One `README.md` with all sections (overview, architecture, install, API, dashboards, deployment, FAQ).
**Alternatives considered:** Separate docs/ directory with multiple files. Overkill for initial release.

**Rationale:** Single file is easier to maintain and read. GitHub renders it on the repo homepage.

### Decision 4: Idempotent by checking state before each step

**Chosen:** Before downloading Grafana, check if the binary exists. Before `pip install`, check if flask is importable. Before copying dashboards, check if target exists.
**Rationale:** Makes `./install.sh` safe to re-run after partial failures or upgrades.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Grafana download URL changes between versions | Document the URL at top of install.sh as a variable. Easy to update. |
| pip vs pip3 confusion on some distros | Try `pip3` first, fall back to `pip`. Document in README. |
| Grafana plugins installation requires network | Check for internet before plugin install steps. |
| README screenshots go stale as dashboards evolve | Use placeholder text initially; add screenshots post-implementation. |
