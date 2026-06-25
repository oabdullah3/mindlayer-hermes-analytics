## ADDED Requirements

### Requirement: Sidebar navigation

The dashboard portal SHALL provide sidebar navigation linking to all dashboard pages.

#### Scenario: Dashboard is loaded

- **WHEN** the user opens the dashboard application
- **THEN** the sidebar displays navigation links for: Home (portal), Session Overview, Skills, Tools

#### Scenario: User clicks a navigation link

- **WHEN** the user clicks a navigation item in the sidebar
- **THEN** the dashboard navigates to the corresponding page without a full page reload

### Requirement: Shared data loading layer

The portal SHALL load the snapshot once at startup and share it across all dashboard pages via session state.

#### Scenario: Dashboard loads for the first time

- **WHEN** the dashboard application starts
- **THEN** it fetches `GET {API_BASE_URL}/api/snapshots/latest`, stores the result in `st.session_state.snapshot`, and all pages read from this shared state

#### Scenario: API is unavailable

- **WHEN** the API server is not running or returns an error
- **THEN** the dashboard displays a banner: "Cannot connect to Hermes Analytics API at {API_BASE_URL}. Make sure the server is running." and all pages render their empty states

#### Scenario: Snapshot is empty or missing

- **WHEN** the API returns a snapshot with zero sessions or a 503 status
- **THEN** the dashboard stores `None` in session state and all pages render their empty states

### Requirement: API base URL configuration

The portal SHALL read the API base URL from an environment variable.

#### Scenario: API_BASE_URL is set

- **WHEN** the `API_BASE_URL` environment variable is set (e.g., `http://192.168.1.100:5555`)
- **THEN** the dashboard uses that URL for all API calls

#### Scenario: API_BASE_URL is not set

- **WHEN** the `API_BASE_URL` environment variable is not set
- **THEN** the dashboard defaults to `http://localhost:5555`

### Requirement: Landing page with cross-domain summary

The portal's home page SHALL display a cross-domain summary drawn from the snapshot.

#### Scenario: Snapshot is loaded with data

- **WHEN** the snapshot is available and contains data
- **THEN** the home page displays summary cards for: total sessions, total messages, total skill loads, total tool calls, unique models, unique platforms, and the `generated_at` timestamp

#### Scenario: Snapshot is not available

- **WHEN** the snapshot is `None` or empty
- **THEN** the home page displays "No data available. Run the collector and refresh."

### Requirement: Top skills and tools preview

The portal's home page SHALL show a preview of the top 5 skills and top 5 tools.

#### Scenario: Snapshot has skills and tools data

- **WHEN** the snapshot contains global insights with skills and tools
- **THEN** the home page renders two small tables or bar charts: top 5 skills by load count and top 5 tools by call count, each with a "View all" link to the respective dashboard page

#### Scenario: Snapshot has no skills or tools

- **WHEN** skills or tools data is unavailable
- **THEN** the respective preview section is hidden or shows "No data"

### Requirement: Consistent page layout

The portal SHALL enforce a consistent visual layout across all dashboard pages.

#### Scenario: Any dashboard page is rendered

- **WHEN** the user navigates to any page (overview, detail, skills, tools)
- **THEN** the page uses the same header style, navigation sidebar, and empty-state patterns as the portal home page

### Requirement: Session detail navigation from overview

The portal SHALL enable navigation from the session overview table to the session detail page.

#### Scenario: User selects a session from the overview

- **WHEN** the user clicks a session row in the session overview page
- **THEN** the portal stores the selected `session_id` in `st.session_state` and navigates to the session detail page, which reads that ID to find and display the session

### Requirement: Back navigation from detail to overview

The session detail page SHALL provide a way to return to the session overview.

#### Scenario: User is viewing a session detail

- **WHEN** the user is on the session detail page
- **THEN** a "Back to Sessions" button or link is visible that navigates back to the session overview page

### Requirement: Error boundary for per-page rendering failures

The portal SHALL catch rendering errors on individual pages and display a fallback message instead of crashing the entire app.

#### Scenario: A dashboard page encounters an unexpected error

- **WHEN** a page raises an exception during rendering (e.g., malformed data)
- **THEN** the portal displays an error message on that page: "Something went wrong rendering this page. Check the logs for details." Other pages remain functional
