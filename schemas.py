"""Slash command parameter schemas for hermes-snapshot-analytics."""

HERMES_SNAPSHOT_ANALYTICS = {
    "name": "hermes-snapshot-analytics",
    "description": (
        "Start Hermes Analytics: runs the collector, starts a local dashboard, "
        "and returns the URL. The snapshot is pushed to the local server and "
        "optionally to the company-wide remote dashboard."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "server_port": {
                "type": "integer",
                "description": "Port for the local analytics server (default: 5555)",
            },
            "dashboard_port": {
                "type": "integer",
                "description": "Port for the local dashboard (default: 8501)",
            },
        },
        "required": [],
    },
}
