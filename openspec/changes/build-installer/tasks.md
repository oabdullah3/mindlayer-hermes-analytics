## 1. install.sh — Python Dependencies

- [x] 1.1 Create `install.sh` with shebang, `set -euo pipefail`, and color-coded log functions (info, success, warn, error)
- [x] 1.2 Check for `pip3` or `pip` availability
- [x] 1.3 Run `pip install -r requirements.txt`
- [x] 1.4 Handle missing pip with clear error and exit
- [x] 1.5 Add idempotency check: skip install if packages already importable

## 2. install.sh — Userend Config

- [x] 2.1 Check if `userend/install.sh` exists and is executable
- [x] 2.2 Run `userend/install.sh` for per-user config (username, remote URL)
- [x] 2.3 If `~/.hermes-analytics.conf` already exists, skip with message "Already configured"

## 3. install.sh — Initial Data & Summary

- [x] 3.1 Run `python3 collector.py` for initial snapshot
- [x] 3.2 Print success summary: collector output, config status, runtime paths
- [x] 3.3 Print instructions to start: `python server.py &` and `streamlit run dashboard.py`

## 4. README.md

- [x] 4.1 Write project title, one-line description, and key selling points
- [x] 4.2 Include ASCII architecture diagram with Mode A/B labels (Streamlit dashboard, not Grafana)
- [x] 4.3 Write Local Setup (Mode A) instructions: clone → install.sh → start server → start dashboard → open browser
- [x] 4.4 Write Remote Setup (Mode B) instructions: server setup + collector config with HERMES_ANALYTICS_REMOTE
- [x] 4.5 Include API reference table: all endpoints with method, path, description
- [x] 4.6 Document all 5 dashboard pages with ⭐ markers for primary pages
- [x] 4.7 Include deployment scenarios table
- [x] 4.8 Add Open Questions / Future Roadmap section
- [x] 4.9 Add file structure tree
- [x] 4.10 Final README consistency pass: flip all remaining ⬜ planned markers to ✅, verify sections match actual implementation, ensure quick-start commands work end-to-end
