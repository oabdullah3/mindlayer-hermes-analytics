## Context

The project consists of three independently-built components (collector, REST API, Streamlit dashboards) that must work together. A user cloning the repo faces several manual steps: install Python dependencies, configure the userend client, run an initial collection, and start the server and dashboard. `install.sh` collapses this into one command. `README.md` is the project's front door.

Current state: No installer or README exists. The repository contains only the collector, server, PLAN.md, and the openspec scaffolding.

Constraints:
- Must work on Linux — pure Python, no platform-specific binaries
- Must be idempotent (safe to run `./install.sh` multiple times)
- Must not require root privileges

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
- Systemd service files (manual start is fine for v1)
- Uninstall script
- Package manager integration (apt, brew)

## Decisions

### Decision 1: Bash over Python for install script

**Chosen:** Plain bash script — no Python dependency for installation itself.
**Rationale:** The install script installs Python dependencies. Using Python for the installer creates a chicken-and-egg problem. Bash is universally available on Linux.

### Decision 2: Python virtual environment recommended, not enforced

**Chosen:** Install dependencies with `pip install -r requirements.txt` (streamlit, plotly, flask). Offer `python3 -m venv .venv` as optional step. Do not enforce.
**Rationale:** Some users already have these packages available system-wide. The install script detects if the packages are importable before installing.

### Decision 3: README as single comprehensive document

**Chosen:** One `README.md` with all sections (overview, architecture, install, API, dashboards, deployment, FAQ).
**Alternatives considered:** Separate docs/ directory with multiple files. Overkill for initial release.

**Rationale:** Single file is easier to maintain and read. GitHub renders it on the repo homepage.

### Decision 4: Idempotent by checking state before each step

**Chosen:** Before `pip install`, check if required packages are importable. Before running collector, check if `snapshot_latest.json` exists. Before `userend/install.sh`, check if `~/.hermes-analytics.conf` exists.
**Rationale:** Makes `./install.sh` safe to re-run after partial failures or upgrades.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| pip vs pip3 confusion on some distros | Try `pip3` first, fall back to `pip`. Document in README. |
| README screenshots go stale as dashboards evolve | Use placeholder text initially; add screenshots post-implementation. |
