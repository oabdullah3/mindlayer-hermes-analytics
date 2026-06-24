## Context

Grafana dashboards are defined as provisioned JSON files — no manual UI clicking. Each dashboard is a self-contained JSON document specifying panels, datasource queries, variables, and layout. Dashboards are discovered by Grafana on startup from the provisioning directory.

The two primary dashboards (skills, tools) are the USP of Hermes Analytics. Two supporting dashboards (session overview, session detail with drill-down linking) complete the picture.

Current state: No dashboards exist. The REST API serves JSON but nothing visualizes it.

Constraints:
- Dashboards must work with either datasource (SQLite for local, Infinity/JSON for remote)
- Must use Grafana's built-in time range filtering
- Must support dashboard linking (session overview → session detail)
- Must be portable (no absolute paths, use `$HERMES_HOME` variable)

## Goals / Non-Goals

**Goals:**
- 4 fully functional dashboards with all panels specified in PLAN.md
- Zero-click provisioning: drop JSON files into `grafana/provisioning/dashboards/` and they appear
- Both datasource configs ready (local and remote)
- Dashboard linking from session overview to session detail
- Time range picker support on all time-series panels
- Templating variables: `$skill`, `$tool`, `$session` dropdowns where applicable

**Non-Goals:**
- Custom Grafana panel plugins — use only built-in and datasource plugin panel types
- Alerting rules — out of scope for initial release
- Grafana Cloud configuration — local and self-hosted only
- Panel-by-panel embedding configuration (kiosk mode is documented in PLAN.md, not implemented here)

## Decisions

### Decision 1: Grafana 13.1.0+ JSON schema

**Chosen:** Target Grafana v13.x dashboard JSON schema. Use `schemaVersion` appropriate to v13.
**Rationale:** v13 is the current stable OSS release. The plan specifies v13.1.1.

### Decision 2: Panel types chosen for each metric

**Chosen:**
- Bar gauge for leaderboards (skills/tools by count) — vertical ranking, space-efficient
- Time series for timelines — stacked by name, daily aggregation
- Table for detail lists (token cost, sessions) — sortable, exportable
- Stat for single-number KPIs (session count, error count)
- Pie chart for proportions (platform split, auto-vs-manual)
- Heatmap for co-occurrence matrix
- Histogram for distribution (skills per session)
- Logs panel for error display

**Rationale:** These are all built-in Grafana panel types. No custom plugins needed.

### Decision 3: SQL queries in dashboard JSON for local mode

**Chosen:** Embed SQL queries (from PLAN.md) directly in the dashboard JSON panel definitions using the `frser-sqlite-datasource` query format.
**Rationale:** SQLite datasource supports raw SQL. Queries are parameterized with Grafana's `$__timeFilter()` and `$__timeFrom()`/`$__timeTo()` macros for time range filtering.

### Decision 4: Separate dashboards for local vs remote or conditional datasource

**Chosen:** A single set of dashboards that works with either datasource. Users configure which datasource to use via provisioning.
**Rationale:** Avoids dashboard duplication. The datasource YAML points to either SQLite (local) or Infinity (remote). Dashboards reference the datasource by name.

### Decision 5: Dashboard linking via Grafana's built-in data links

**Chosen:** Session table rows in Dashboard 3 (session overview) include a data link to Dashboard 4 (session detail) passing `$__cell_1` (session ID) as a variable.
**Rationale:** Native Grafana feature — no custom code needed.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| SQL queries assume Unix timestamps in state.db | Hermes uses Unix timestamps. Add `datetime(timestamp, 'unixepoch')` conversion in queries. |
| `frser-sqlite-datasource` plugin may lag Grafana versions | Pin to tested version (v4.0.6). Test before upgrading. |
| JSON API dashboards (Infinity) may be slower than direct SQLite | Infinity caches responses. For remote mode, network latency dominates anyway. |
| Dashboard JSON schema changes between Grafana versions | Pin `schemaVersion` in dashboard JSON. Test against v13.1.x only. |
| `$HERMES_HOME` resolved differently by Grafana vs collector | Use an absolute path or documented symlink. Document in README. |

## Open Questions

1. Should we provide a "dark mode" and "light mode" variant of each dashboard, or stick with one?
2. Should the co-occurrence heatmap use raw counts or normalized (percentage of sessions)?
3. Should we include a "getting started" dashboard with a walkthrough of each panel?
