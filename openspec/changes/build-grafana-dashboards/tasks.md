## 1. Directory Structure & Datasources

- [ ] 1.1 Create `grafana/provisioning/dashboards/` directory
- [ ] 1.2 Create `grafana/provisioning/datasources/` directory
- [ ] 1.3 Create `sqlite-datasource.yaml` — configure `frser-sqlite-datasource` with path to `~/.hermes/state.db`
- [ ] 1.4 Create `infinity-datasource.yaml` — configure `yesoreyeram-infinity-datasource` with base URL `http://localhost:5555/api/`

## 2. Skills Analytics Dashboard (⭐ Primary USP)

- [ ] 2.1 Create `skills-analytics.json` dashboard scaffold with title, uid, schemaVersion, time range defaults
- [ ] 2.2 Add Skill Load Leaderboard bar gauge panel with SQL query sorted by load_count DESC
- [ ] 2.3 Add Skill Load Timeline time series panel with daily aggregation stacked by skill name
- [ ] 2.4 Add Skill Token Cost table panel with columns: skill_name, loads, total_chars, token_estimate, est_cost_usd
- [ ] 2.5 Add Skill Load Histogram panel (distribution of skills-per-session counts)
- [ ] 2.6 Add Top Skills Weekly Trend time series panel (top 5 skills, weekly aggregation)
- [ ] 2.7 Add Auto vs Manual pie chart panel (inferred from preceding_user_message content)
- [ ] 2.8 Add `$skill` template variable for cross-panel filtering

## 3. Tools Analytics Dashboard (⭐ Primary USP)

- [ ] 3.1 Create `tools-analytics.json` dashboard scaffold with title, uid, schemaVersion
- [ ] 3.2 Add Tool Call Leaderboard bar gauge panel with SQL query sorted by call_count DESC
- [ ] 3.3 Add Tool Call Timeline time series panel with daily aggregation stacked by tool name
- [ ] 3.4 Add Tool Execution Duration table panel (call_count, avg_duration, max_duration from log_payloads)
- [ ] 3.5 Add Tool Errors stat panel (total errors, error rate %)
- [ ] 3.6 Add Tool Co-occurrence Heatmap panel (which tools appear together in sessions)
- [ ] 3.7 Add Terminal Usage Breakdown pie chart (success vs error vs timeout)
- [ ] 3.8 Add `$tool` template variable for cross-panel filtering

## 4. Session Overview Dashboard

- [ ] 4.1 Create `session-overview.json` dashboard scaffold
- [ ] 4.2 Add Session Count stat panel
- [ ] 4.3 Add Token Consumption time series (input/output tokens per day)
- [ ] 4.4 Add Cost Over Time time series (estimated USD per day)
- [ ] 4.5 Add Session List table panel with columns: session_id, platform, model, messages, tools, skills, tokens, cost
- [ ] 4.6 Add data link on session_id column that links to session-detail dashboard passing session ID as variable
- [ ] 4.7 Add Platform Split pie chart (telegram vs discord vs cli)
- [ ] 4.8 Add Model Usage bar gauge (sessions per model)

## 5. Session Detail Dashboard

- [ ] 5.1 Create `session-detail.json` dashboard scaffold with `$session` variable from dashboard link
- [ ] 5.2 Add Session Header text/stat panel (session_id, platform, model, duration, chat_name)
- [ ] 5.3 Add Token Breakdown bar gauge (input, output, cache_read, cache_write, reasoning)
- [ ] 5.4 Add Skills Loaded table panel (skill_name, load_timestamp, preceding_user_message truncated)
- [ ] 5.5 Add Tool Calls bar chart panel (tool_name vs call_count within session)
- [ ] 5.6 Add User Messages table panel (message_id, timestamp, content truncated to 200 chars)
- [ ] 5.7 Add Errors log panel (timestamp, error message from session errors array)

## 6. Validation

- [ ] 6.1 Verify all dashboard JSON files parse as valid JSON
- [ ] 6.2 Verify datasource references match the names in datasource YAML files
- [ ] 6.3 Verify dashboard UIDs are unique across all 4 dashboards
- [ ] 6.4 Verify time range macros (`$__timeFilter`, `$__timeFrom`, `$__timeTo`) are used in all SQL queries

## 7. Documentation

- [ ] 7.1 Update README.md: mark Grafana dashboards as ✅ in project status table, update dashboard descriptions with actual panel counts, add `http://localhost:3000` access instructions if not present
