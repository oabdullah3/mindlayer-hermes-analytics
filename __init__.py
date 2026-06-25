"""Hermes Analytics Plugin — registration, slash command, and CLI command.

Registers /hermes-snapshot-analytics in Hermes chat sessions and
hermes snapshot-analytics as a standalone CLI subcommand.

Both start a local Flask server, run the collector, launch a local
Streamlit dashboard, and return the URL.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).parent
_REPO_ROOT = _PLUGIN_DIR  # now at repo root, both are the same

# PID file paths
_SERVER_PID_FILE = "/tmp/hermes-analytics-server.pid"
_DASHBOARD_PID_FILE = "/tmp/hermes-analytics-dashboard.pid"

_DEFAULT_SERVER_PORT = 5555
_DEFAULT_DASHBOARD_PORT = 8501
_MAX_PORT_TRIES = 20

# Hardcoded remote URL — override with HERMES_ANALYTICS_REMOTE env var
_HARDCODED_REMOTE_URL = os.environ.get("HERMES_ANALYTICS_REMOTE", "")


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _is_port_free(port: int) -> bool:
    """Check if a TCP port is available."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _find_free_port(start: int) -> int:
    """Find a free port starting from `start`, incrementing up to _MAX_PORT_TRIES times."""
    for offset in range(_MAX_PORT_TRIES):
        port = start + offset
        if _is_port_free(port):
            return port
    return start  # fallback — let it fail naturally


def _wait_for_health(url: str, timeout: float = 5.0) -> bool:
    """Poll /api/health until it returns 200 or timeout expires."""
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.3)
    return False


def _kill_from_pid_file(pid_file: str) -> bool:
    """Read a PID file and kill the process. Remove the file afterwards."""
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        # Wait a bit for graceful shutdown
        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                break
        else:
            # Still alive — force kill
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        os.remove(pid_file)
        return True
    except (FileNotFoundError, ValueError, OSError) as e:
        logger.debug("Could not kill process from %s: %s", pid_file, e)
        return False


def _resolve_username() -> str:
    """Resolve the analytics username from env or system."""
    return os.environ.get("HERMES_ANALYTICS_USER") or os.environ.get("USER") or os.uname().nodename


# ──────────────────────────────────────────────────────────────────────
# Slash command handler
# ──────────────────────────────────────────────────────────────────────

def _ensure_dependencies() -> str | None:
    """Auto-install missing Python packages into the running environment.

    Hermes plugins run in a venv or managed Python that may not have pip
    bootstrapped.  We handle four scenarios:

    1. Dependencies already importable → no-op
    2. pip missing from the interpreter → bootstrap via ensurepip (stdlib)
    3. PEP 668 externally-managed-environment → retry with --break-system-packages
    4. Everything else → report the error with a manual fallback
    """
    required = ("flask", "streamlit", "plotly")
    missing = [p for p in required]
    for pkg in required:
        try:
            __import__(pkg)
            missing.remove(pkg)
        except ImportError:
            pass
    if not missing:
        return None

    logger.info("Auto-installing missing dependencies: %s", missing)
    reqs_path = _PLUGIN_DIR / "requirements.txt"

    def _run_pip(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
        cmd = [sys.executable, "-m", "pip"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    # ── Step 0: bootstrap pip if the interpreter is missing it ──
    # Hermes may ship a venv without pip.  ensurepip is always present (3.4+).
    have_pip = False
    try:
        check = _run_pip(["--version"], timeout=10)
        have_pip = check.returncode == 0
    except Exception:
        pass

    if not have_pip:
        logger.info("pip not available — bootstrapping via ensurepip")
        bootstrap = subprocess.run(
            [sys.executable, "-m", "ensurepip", "--upgrade", "--default-pip"],
            capture_output=True, text=True, timeout=60,
        )
        if bootstrap.returncode != 0:
            tail = bootstrap.stderr.strip().split("\n")[-5:]
            return (
                "❌ Could not bootstrap pip in the Hermes Python environment.\n\n"
                "```\n" + "\n".join(tail) + "\n```\n\n"
                f"Try manually:\n```bash\n"
                f"cd {_PLUGIN_DIR}\n"
                f"{sys.executable} -m ensurepip --upgrade\n"
                f"{sys.executable} -m pip install -r requirements.txt\n```"
            )

    # ── Step 1: install ──
    result = _run_pip(["install", "-r", str(reqs_path)])
    if result.returncode != 0 and "externally-managed" in result.stderr:
        logger.info("PEP 668 detected — retrying with --break-system-packages")
        result = _run_pip(["install", "--break-system-packages", "-r", str(reqs_path)])

    if result.returncode != 0:
        stderr_tail = result.stderr.strip().split("\n")[-5:]
        return (
            "❌ Auto-install of dependencies failed.\n\n"
            "```\n" + "\n".join(stderr_tail) + "\n```\n\n"
            f"Try manually:\n```bash\n"
            f"cd {_PLUGIN_DIR}\n"
            f"{sys.executable} -m pip install -r requirements.txt\n```"
        )

    # ── Step 2: verify ──
    still_missing = []
    for pkg in missing:
        try:
            __import__(pkg)
        except ImportError:
            still_missing.append(pkg)
    if still_missing:
        return (
            f"❌ pip install succeeded but import still fails: {', '.join(still_missing)}\n\n"
            f"Try manually:\n```bash\n"
            f"cd {_PLUGIN_DIR}\n"
            f"{sys.executable} -m pip install -r requirements.txt\n```"
        )

    logger.info("Auto-install complete — %s are ready", ", ".join(missing))
    return None


def _handle_snapshot_analytics(raw_args: str) -> str:
    """Handler for /hermes-snapshot-analytics.

    Orchestrates: start local server → collect snapshot → start dashboard → return URL.
    """
    # ── 0. Dependency check (auto-install if missing) ──
    dep_err = _ensure_dependencies()
    if dep_err:
        return dep_err

    # Parse optional port args
    server_port = _DEFAULT_SERVER_PORT
    dashboard_port = _DEFAULT_DASHBOARD_PORT
    if raw_args:
        for part in raw_args.strip().split():
            if part.startswith("--server-port="):
                try:
                    server_port = int(part.split("=", 1)[1])
                except ValueError:
                    pass
            elif part.startswith("--dashboard-port="):
                try:
                    dashboard_port = int(part.split("=", 1)[1])
                except ValueError:
                    pass

    messages: list[str] = []
    started_server = False

    # ── 1. Start local Flask server ─────────────────────────────────
    actual_server_port = _find_free_port(server_port)
    if actual_server_port != server_port:
        messages.append(f"Port {server_port} occupied — using port {actual_server_port}")

    server_proc = subprocess.Popen(
        [sys.executable, str(_PLUGIN_DIR / "server.py")],
        env={**os.environ, "PORT": str(actual_server_port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    with open(_SERVER_PID_FILE, "w") as f:
        f.write(str(server_proc.pid))

    server_url = f"http://localhost:{actual_server_port}"
    health_url = f"{server_url}/api/health"

    if not _wait_for_health(health_url, timeout=10.0):
        # Check if process died immediately (import error, port conflict, etc.)
        time.sleep(0.5)
        exit_code = server_proc.poll()
        if exit_code is not None:
            stderr_out = server_proc.stderr.read().decode("utf-8", errors="replace").strip() if server_proc.stderr else ""
            stdout_out = server_proc.stdout.read().decode("utf-8", errors="replace").strip() if server_proc.stdout else ""
            error_detail = stderr_out or stdout_out or f"exit code {exit_code}"
            _kill_from_pid_file(_SERVER_PID_FILE)
            # If it's a missing module, add install hint
            hint = ""
            if "ModuleNotFoundError" in error_detail or "ImportError" in error_detail:
                hint = f"\n\nRun the installer to get dependencies:\n```bash\ncd {_PLUGIN_DIR} && ./install.sh\n```"
            return f"❌ Analytics server crashed on startup:\n```\n{error_detail[:500]}\n```{hint}"
        _kill_from_pid_file(_SERVER_PID_FILE)
        return (
            f"❌ Analytics server failed to start within 10 seconds.\n"
            f"Is Flask installed? Run the installer:\n"
            f"```bash\ncd {_PLUGIN_DIR} && ./install.sh\n```\n"
            f"Is port {actual_server_port} available?"
        )

    started_server = True

    # ── 2. Run the collector ────────────────────────────────────────
    collector_env = {
        **os.environ,
        "HERMES_ANALYTICS_SERVER_PORT": str(actual_server_port),
        "HERMES_ANALYTICS_USER": _resolve_username(),
    }
    if _HARDCODED_REMOTE_URL:
        collector_env["HERMES_ANALYTICS_REMOTE"] = _HARDCODED_REMOTE_URL

    collector_result = subprocess.run(
        [sys.executable, str(_PLUGIN_DIR / "collector.py")],
        env=collector_env,
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )

    if collector_result.returncode != 0:
        # Collector failed — clean up server
        _kill_from_pid_file(_SERVER_PID_FILE)
        error_msg = collector_result.stderr.strip() or collector_result.stdout.strip() or "Unknown error"
        return f"❌ Snapshot collection failed:\n```\n{error_msg[:500]}\n```"

    # Parse collector output for push results
    collector_stdout = collector_result.stdout.strip()
    push_info = ""
    for line in collector_stdout.split("\n"):
        if "Pushed to" in line or "Saved locally" in line:
            push_info += f"\n{line.strip()}"

    # ── 3. Start local Streamlit dashboard ──────────────────────────
    actual_dashboard_port = _find_free_port(dashboard_port)
    if actual_dashboard_port != dashboard_port:
        messages.append(f"Dashboard port {dashboard_port} occupied — using port {actual_dashboard_port}")

    dash_proc = subprocess.Popen(
        ["streamlit", "run", str(_PLUGIN_DIR / "dashboard.py"),
         "--server.port", str(actual_dashboard_port),
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        env={**os.environ, "API_BASE_URL": server_url},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with open(_DASHBOARD_PID_FILE, "w") as f:
        f.write(str(dash_proc.pid))

    dashboard_url = f"http://localhost:{actual_dashboard_port}"

    # ── 4. Build response ───────────────────────────────────────────
    response_lines = [
        "✅ **Hermes Analytics is ready!**",
        "",
        f"📊 **Your dashboard:** {dashboard_url}",
    ]

    if push_info:
        response_lines.append(push_info)

    if _HARDCODED_REMOTE_URL:
        response_lines.append(f"🏢 **Company dashboard:** {_HARDCODED_REMOTE_URL}")

    response_lines.extend([
        "",
        "Use the **🛑 Shutdown Analytics** button in the dashboard sidebar to stop all analytics processes.",
        "Closing the browser tab will NOT stop the services — only the button does.",
    ])

    if messages:
        response_lines.insert(2, f"ℹ️ {'; '.join(messages)}")

    return "\n".join(response_lines)


# ──────────────────────────────────────────────────────────────────────
# CLI command: hermes snapshot-analytics
# ──────────────────────────────────────────────────────────────────────

def _cli_handler(args):
    """Handler for `hermes snapshot-analytics` — adapt argparse → slash handler."""
    raw_args_parts = []
    if getattr(args, "server_port", None):
        raw_args_parts.append(f"--server-port={args.server_port}")
    if getattr(args, "dashboard_port", None):
        raw_args_parts.append(f"--dashboard-port={args.dashboard_port}")
    raw_args = " ".join(raw_args_parts)

    result = _handle_snapshot_analytics(raw_args)
    # Strip markdown formatting for clean terminal output
    for char in ("*", "`", "#"):
        result = result.replace(char, "")
    print(result)


def _setup_argparse(subparser):
    """Build the argparse tree for `hermes snapshot-analytics`."""
    subparser.add_argument(
        "--server-port", type=int, default=None,
        help=f"Port for the local analytics server (default: {_DEFAULT_SERVER_PORT})",
    )
    subparser.add_argument(
        "--dashboard-port", type=int, default=None,
        help=f"Port for the Streamlit dashboard (default: {_DEFAULT_DASHBOARD_PORT})",
    )
    subparser.set_defaults(func=_cli_handler)


# ──────────────────────────────────────────────────────────────────────
# Plugin registration
# ──────────────────────────────────────────────────────────────────────

def register(ctx):
    """Register the slash command and CLI subcommand."""
    ctx.register_command(
        "hermes-snapshot-analytics",
        handler=_handle_snapshot_analytics,
        description="Start Hermes Analytics: collect snapshot, launch local dashboard",
    )

    ctx.register_cli_command(
        name="snapshot-analytics",
        help="Start the Hermes Analytics server, collector, and dashboard",
        setup_fn=_setup_argparse,
        handler_fn=_cli_handler,
    )

    logger.info("Hermes Analytics plugin registered — /hermes-snapshot-analytics available")
