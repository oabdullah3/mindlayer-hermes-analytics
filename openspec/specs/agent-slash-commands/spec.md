## ADDED Requirements

### Requirement: hermes-snapshot shell wrapper exists

A shell script SHALL exist at `userend/hermes-snapshot` that wraps the collector for agent invocation. The script SHALL source `~/.hermes-analytics.conf`, run the collector, and output an inline summary.

#### Scenario: Agent invokes /hermes-snapshot

- **WHEN** `userend/hermes-snapshot` is executed
- **THEN** the collector runs against `$HERMES_HOME` (or `~/.hermes`)
- **AND** an inline summary is printed to stdout with session count, skill count, tool count, shell command count, and error count

#### Scenario: Config file is missing

- **WHEN** `userend/hermes-snapshot` is executed and `~/.hermes-analytics.conf` does not exist
- **THEN** the script prints "Run userend/install.sh first to configure Hermes Analytics" and exits with code 1

### Requirement: Inline summary format

After a successful collection, the agent SHALL receive a compact inline summary with the following format:

```
📊 Hermes Analytics Snapshot
   Sessions: <N>
   Skills loaded: <N> (top: <skill_name> ×<count>)
   Tool calls: <N> across <N> tools
   Shell commands: <N> (<N> failed)
   Errors: <N>
   Pushed to: <url> ✅ (or "Saved locally")
```

#### Scenario: Successful collection with remote push

- **WHEN** the collector runs and `HERMES_ANALYTICS_REMOTE` is set and push succeeds
- **THEN** the summary shows "Pushed to: <url> ✅"

#### Scenario: Successful collection without remote

- **WHEN** the collector runs and `HERMES_ANALYTICS_REMOTE` is unset
- **THEN** the summary shows "Saved locally"

#### Scenario: Collection fails

- **WHEN** the collector exits with a non-zero code
- **THEN** the summary shows "❌ Collection failed: <error message>"

### Requirement: /hermes-snapshot dashboard variant

The shell wrapper SHALL support a `dashboard` subcommand that additionally prints the local dashboard URL after the inline summary.

#### Scenario: Dashboard subcommand

- **WHEN** `userend/hermes-snapshot dashboard` is executed
- **THEN** the inline summary is displayed followed by "📊 Dashboard: http://localhost:3000"

### Requirement: Slash command registration is documented

The `userend/` directory SHALL include documentation (in README or a separate file) specifying how to register `/hermes-snapshot` and `/hermes-snapshot dashboard` as agent slash commands, including the command to invoke and expected working directory.

#### Scenario: User setting up agent integration

- **WHEN** a user reads the userend documentation
- **THEN** they find clear instructions for registering the slash commands in their agent platform

### Requirement: Agent auto-detection is a non-blocking enhancement

The shell wrapper SHALL NOT auto-trigger without user invocation. The agent MAY offer to run `/hermes-snapshot` when detecting analytics-relevant context, but this is a UX enhancement, not a requirement.

#### Scenario: Agent detects analytics context

- **WHEN** a user asks "how many skills have I loaded recently?"
- **THEN** the agent MAY offer to run `/hermes-snapshot` but MUST NOT execute it without user consent
