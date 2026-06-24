## 1. install.sh — Grafana Setup

- [ ] 1.1 Create `install.sh` with shebang, `set -euo pipefail`, and color-coded log functions (info, success, warn, error)
- [ ] 1.2 Add `GRAFANA_VERSION` and `GRAFANA_URL` variables at top of script
- [ ] 1.3 Implement Grafana download step: check if `./grafana-server/grafana-server` exists, if not, wget + tar extract
- [ ] 1.4 Handle missing `wget` with clear error message and exit code 1

## 2. install.sh — Plugin Installation

- [ ] 2.1 Implement `grafana-cli plugins install frser-sqlite-datasource` step
- [ ] 2.2 Implement `grafana-cli plugins install yesoreyeram-infinity-datasource` step
- [ ] 2.3 Add idempotency check: skip plugin install if already present in Grafana's plugin dir

## 3. install.sh — Provisioning & Config

- [ ] 3.1 Copy `grafana/provisioning/dashboards/*.json` to `grafana-server/conf/provisioning/dashboards/`
- [ ] 3.2 Copy `grafana/provisioning/datasources/*.yaml` to `grafana-server/conf/provisioning/datasources/`
- [ ] 3.3 Configure `allow_embedding = true` in grafana.ini `[security]` section
- [ ] 3.4 Configure `[auth.proxy]` section in grafana.ini (enabled, header_name, auto_sign_up)

## 4. install.sh — Python Dependencies

- [ ] 4.1 Check for `pip3` or `pip` availability
- [ ] 4.2 Run `pip install -r requirements.txt`
- [ ] 4.3 Handle missing pip with clear error and exit

## 5. install.sh — Initial Data & Summary

- [ ] 5.1 Run `python3 collector.py` for initial snapshot
- [ ] 5.2 Print success summary: Grafana binary path, plugin list, dashboard URLs, server start command
- [ ] 5.3 Print instructions to start: `python server.py &` and `./grafana-server`

## 6. README.md

- [ ] 6.1 Write project title, one-line description, and key selling points
- [ ] 6.2 Include ASCII architecture diagram (from PLAN.md) with Mode A/B labels
- [ ] 6.3 Write Local Setup (Mode A) instructions: clone → install.sh → start server → start Grafana → open browser
- [ ] 6.4 Write Remote Setup (Mode B) instructions: server setup + collector config with HERMES_ANALYTICS_REMOTE
- [ ] 6.5 Include API reference table: all 10 endpoints with method, path, description
- [ ] 6.6 Document all 4 dashboards with panel lists, marking skills and tools with ⭐
- [ ] 6.7 Include deployment scenarios table (from PLAN.md)
- [ ] 6.8 Add Open Questions / Future Roadmap section
- [ ] 6.9 Add file structure tree (from PLAN.md)
