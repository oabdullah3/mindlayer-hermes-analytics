## 1. Setup & Dependencies

- [ ] 1.1 Add `streamlit` and `plotly` to `requirements.txt`
- [ ] 1.2 Create `dashboard.py` with Streamlit app scaffolding: `st.set_page_config` (title, icon, layout), imports for streamlit, plotly, requests, json, os

## 2. Portal Framework (dashboard-portal)

- [ ] 2.1 Implement `API_BASE_URL` configuration: read from `os.environ.get("API_BASE_URL", "http://localhost:5555")`
- [ ] 2.2 Implement shared data loading: on first load, `requests.get(f"{API_BASE_URL}/api/snapshots/latest")` and store in `st.session_state.snapshot`; handle connection errors and empty responses
- [ ] 2.3 Implement sidebar navigation using `st.navigation` with `st.Page` objects for: Portal Home, Session Overview, Session Detail (dynamic), Skills, Tools
- [ ] 2.4 Implement consistent page layout: shared header/style, error boundary via try/except in each page function
- [ ] 2.5 Implement Portal Home page: summary cards (total sessions, total messages, total skill loads, total tool calls, unique models, unique platforms, generated_at)
- [ ] 2.6 Implement Portal Home top-N previews: top 5 skills table with "View all → Skills" link, top 5 tools table with "View all → Tools" link

## 3. Session Overview Dashboard

- [ ] 3.1 Implement session list table: `st.dataframe` with columns session_id, model, platform, started_at, duration, token_count, skill_loads_count, tool_calls_count, user_messages_count
- [ ] 3.2 Implement aggregate summary cards at top of overview page using `st.metric`
- [ ] 3.3 Implement model and platform filters via `st.selectbox` that filter the session table and update summary cards
- [ ] 3.4 Implement session timeline chart: Plotly bar chart of sessions per date
- [ ] 3.5 Implement model distribution chart: Plotly horizontal bar chart of sessions per model
- [ ] 3.6 Implement session row click: clicking a session sets `st.session_state.selected_session_id` and navigates to session detail page

## 4. Session Detail Dashboard

- [ ] 4.1 Implement session lookup: read `st.session_state.selected_session_id` or URL param, find matching session in snapshot; display "Session not found" if missing
- [ ] 4.2 Implement session header: display model, platform, chat_name, started_at, ended_at, duration, session_id
- [ ] 4.3 Implement token usage section: render token metrics (input, output, total) from session `tokens`
- [ ] 4.4 Implement skills loaded table: columns skill_name, content_chars, token_estimate, preceding_user_message (truncated), load_timestamp
- [ ] 4.5 Implement tool calls table: columns tool_name, count (as badge), message_ids count
- [ ] 4.6 Implement shell commands table: command string and timestamp
- [ ] 4.7 Implement user messages list: scrollable list with timestamps
- [ ] 4.8 Implement errors section: highlight errors distinct from normal data; hide if empty
- [ ] 4.9 Implement skills vs tools visual breakdown: side-by-side comparison chart
- [ ] 4.10 Add "Back to Sessions" button that clears `selected_session_id` and navigates to overview

## 5. Skills Dashboard

- [ ] 5.1 Implement skills ranking table from `global_insights.skills` (fallback to computing from sessions if missing): columns rank, name, load_count, total_chars, token_estimate, avg_chars_per_load, avg_tokens_per_load
- [ ] 5.2 Implement skills bar chart: Plotly horizontal bar chart of top 10 skills by load count, with "Show all" toggle
- [ ] 5.3 Implement token estimate distribution chart: Plotly histogram of token estimates across skills
- [ ] 5.4 Implement skills usage timeline: Plotly line/bar chart of skill loads per day, one series per skill
- [ ] 5.5 Implement preceding user messages table: most frequent preceding messages with counts
- [ ] 5.6 Implement skill drill-down: clicking a skill name shows filtered sessions that loaded that skill

## 6. Tools Dashboard

- [ ] 6.1 Implement tools ranking table from `global_insights.tools` (fallback to computing from sessions if missing): columns rank, name, call_count, percentage_of_total
- [ ] 6.2 Implement tools bar chart: Plotly horizontal bar chart of all tools by call count
- [ ] 6.3 Implement tools pie/donut chart: Plotly pie chart showing proportion of calls per tool
- [ ] 6.4 Implement tools usage timeline: Plotly line/bar chart of tool calls per day, one series per tool
- [ ] 6.5 Implement session-tool correlation: heatmap or cross-tab table of tool usage across sessions
- [ ] 6.6 Implement tool drill-down: clicking a tool name shows filtered sessions that called that tool
- [ ] 6.7 Implement tool call distribution histogram: Plotly histogram of tool call counts per session

## 7. Empty & Error States

- [ ] 7.1 Implement empty state for session overview when no sessions exist
- [ ] 7.2 Implement empty state for session detail when session_id not found
- [ ] 7.3 Implement empty state for skills page when no skills data exists
- [ ] 7.4 Implement empty state for tools page when no tools data exists
- [ ] 7.5 Implement API connection error banner: displayed when API is unreachable

## 8. Integration & Validation

- [ ] 8.1 Start Flask server: `python server.py` on port 5555
- [ ] 8.2 Run `streamlit run dashboard.py` and verify all 5 pages render with actual snapshot data
- [ ] 8.3 Verify sidebar navigation works across all pages
- [ ] 8.4 Verify session overview → session detail navigation works end-to-end
- [ ] 8.5 Verify empty states render correctly (stop server, verify banner; start server with no snapshot, verify empty pages)
- [ ] 8.6 Verify API_BASE_URL env var: set to a different port, confirm dashboard fails to connect with correct error
- [ ] 8.7 Update README.md: add Streamlit dashboard section with run instructions
