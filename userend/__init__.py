"""Hermes Analytics Plugin — registration + slash command handler.

Registers /hermes-snapshot-analytics in Hermes chat sessions.
The handler starts a local Flask server, runs the collector,
launches a local Streamlit dashboard, and returns the URL.
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
_REPO_ROOT = _PLUGIN_DIR.parent

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
    reqs_path = _REPO_ROOT / "requirements.txt"

    def _run_pip(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
        cmd = [sys.executable, "-m", "pip"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    # ── Step 0: bootstrap pip if the interpreter is missing it ──
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
                f"cd {_REPO_ROOT}\n"
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
            f"cd {_REPO_ROOT}\n"
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
            f"cd {_REPO_ROOT}\n"
            f"{sys.executable} -m pip install -r requirements.txt\n```"
        )

    logger.info("Auto-install complete — %s are ready", ", ".join(missing))
    return None


# ──────────────────────────────────────────────────────────────────────
# Mode: CLI output (printed to stdout, no browser)
# ──────────────────────────────────────────────────────────────────────

def _run_cli_mode(snapshot_path: str | None = None) -> str:
    """Run collector then print CLI metrics. Returns error string or empty string on success."""
    # 1. Run collector to generate snapshot
    collector_env = {
        **os.environ,
        "HERMES_ANALYTICS_USER": _resolve_username(),
    }
    if _HARDCODED_REMOTE_URL:
        collector_env["HERMES_ANALYTICS_REMOTE"] = _HARDCODED_REMOTE_URL

    collector_result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "collector.py")],
        env=collector_env,
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )

    if collector_result.returncode != 0:
        error_msg = collector_result.stderr.strip() or collector_result.stdout.strip() or "Unknown error"
        return f"❌ Snapshot collection failed:\n```\n{error_msg[:500]}\n```"

    # 2. Render CLI output
    from . import cli_metrics

    err = cli_metrics.render_cli(snapshot_path)
    if err:
        return err

    # 3. Show collector push info
    for line in collector_result.stdout.strip().split("\n"):
        if "Pushed to" in line or "Saved locally" in line:
            print(line.strip())

    return ""  # success


# ──────────────────────────────────────────────────────────────────────
# Mode: Browser (Streamlit dashboard)
# ──────────────────────────────────────────────────────────────────────

def _run_browser_mode(
    server_port: int | None = None,
    dashboard_port: int | None = None,
) -> tuple[str, list[str]]:
    """Start server → collector → Streamlit dashboard.

    Returns (error_string, messages_list).  Error is non-empty on failure,
    messages contains port-change notices etc.
    """
    sp = server_port or _DEFAULT_SERVER_PORT
    dp = dashboard_port or _DEFAULT_DASHBOARD_PORT
    messages: list[str] = []

    # ── 1. Start local Flask server ───────────────────────────────
    actual_server_port = _find_free_port(sp)
    if actual_server_port != sp:
        messages.append(f"Port {sp} occupied — using port {actual_server_port}")

    server_proc = subprocess.Popen(
        [sys.executable, str(_REPO_ROOT / "server.py")],
        env={**os.environ, "PORT": str(actual_server_port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    with open(_SERVER_PID_FILE, "w") as f:
        f.write(str(server_proc.pid))

    server_url = f"http://localhost:{actual_server_port}"
    health_url = f"{server_url}/api/health"

    if not _wait_for_health(health_url, timeout=10.0):
        time.sleep(0.5)
        exit_code = server_proc.poll()
        if exit_code is not None:
            stderr_out = server_proc.stderr.read().decode("utf-8", errors="replace").strip() if server_proc.stderr else ""
            stdout_out = server_proc.stdout.read().decode("utf-8", errors="replace").strip() if server_proc.stdout else ""
            error_detail = stderr_out or stdout_out or f"exit code {exit_code}"
            _kill_from_pid_file(_SERVER_PID_FILE)
            return f"❌ Analytics server crashed on startup:\n```\n{error_detail[:500]}\n```", messages
        _kill_from_pid_file(_SERVER_PID_FILE)
        return (
            f"❌ Analytics server failed to start within 10 seconds.\n"
            f"Is Flask installed? Run: `pip install flask`\n"
            f"Is port {actual_server_port} available?"
        ), messages

    # ── 2. Run the collector ──────────────────────────────────────
    collector_env = {
        **os.environ,
        "HERMES_ANALYTICS_SERVER_PORT": str(actual_server_port),
        "HERMES_ANALYTICS_USER": _resolve_username(),
    }
    if _HARDCODED_REMOTE_URL:
        collector_env["HERMES_ANALYTICS_REMOTE"] = _HARDCODED_REMOTE_URL

    collector_result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "collector.py")],
        env=collector_env,
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )

    if collector_result.returncode != 0:
        _kill_from_pid_file(_SERVER_PID_FILE)
        error_msg = collector_result.stderr.strip() or collector_result.stdout.strip() or "Unknown error"
        return f"❌ Snapshot collection failed:\n```\n{error_msg[:500]}\n```", messages

    # Parse collector output for push results
    collector_stdout = collector_result.stdout.strip()
    push_info = ""
    for line in collector_stdout.split("\n"):
        if "Pushed to" in line or "Saved locally" in line:
            push_info += f"\n{line.strip()}"

    # ── 3. Start Streamlit dashboard ──────────────────────────────
    actual_dashboard_port = _find_free_port(dp)
    if actual_dashboard_port != dp:
        messages.append(f"Dashboard port {dp} occupied — using port {actual_dashboard_port}")

    try:
        dash_proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", str(_REPO_ROOT / "dashboard.py"),
             "--server.port", str(actual_dashboard_port),
             "--server.headless", "true",
             "--browser.gatherUsageStats", "false"],
            env={**os.environ, "API_BASE_URL": server_url},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        _kill_from_pid_file(_SERVER_PID_FILE)
        return (
            "❌ Streamlit is not installed on this system.\n"
            "Install it with: pip install streamlit\n"
            "Or use --mode cli for terminal output instead."
        ), messages

    with open(_DASHBOARD_PID_FILE, "w") as f:
        f.write(str(dash_proc.pid))

    # Check if dashboard died immediately
    time.sleep(2)
    exit_code = dash_proc.poll()
    if exit_code is not None:
        _kill_from_pid_file(_SERVER_PID_FILE)
        _kill_from_pid_file(_DASHBOARD_PID_FILE)
        return (
            f"❌ Streamlit dashboard crashed on startup (exit code {exit_code}).\n"
            f"This may happen if Streamlit is not installed or the environment has no display.\n"
            f"Try running with --mode cli for terminal output instead."
        ), messages

    dashboard_url = f"http://localhost:{actual_dashboard_port}"

    if push_info:
        messages.append(push_info.strip())

    if _HARDCODED_REMOTE_URL:
        messages.append(f"Company dashboard: {_HARDCODED_REMOTE_URL}")

    return "", messages + [dashboard_url]


# ──────────────────────────────────────────────────────────────────────
# Slash command handler
# ──────────────────────────────────────────────────────────────────────

def _handle_snapshot_analytics(raw_args: str) -> str:
    """Handler for /hermes-snapshot-analytics.

    Supports --mode (cli|browser|both, default: cli) and --fallback.
    """
    # ── 0. Dependency check ──
    dep_err = _ensure_dependencies()
    if dep_err:
        return dep_err

    # Parse args
    mode = "cli"           # default: CLI (agent can't see browser)
    fallback = False
    server_port: int | None = None
    dashboard_port: int | None = None

    if raw_args:
        for part in raw_args.strip().split():
            if part.startswith("--mode="):
                m = part.split("=", 1)[1].lower()
                if m in ("cli", "browser", "both"):
                    mode = m
            elif part == "--fallback":
                fallback = True
            elif part.startswith("--server-port="):
                try:
                    server_port = int(part.split("=", 1)[1])
                except ValueError:
                    pass
            elif part.startswith("--dashboard-port="):
                try:
                    dashboard_port = int(part.split("=", 1)[1])
                except ValueError:
                    pass

    # ── Execute ──
    if mode == "cli":
        result = _run_cli_mode()
        if result:
            if fallback:
                print("CLI mode failed, falling back to browser mode…")
                err, msgs = _run_browser_mode(server_port, dashboard_port)
                if err:
                    return err
                return _format_browser_response(msgs)
            return result
        return "✅ CLI metrics printed above."

    elif mode == "browser":
        err, msgs = _run_browser_mode(server_port, dashboard_port)
        if err:
            if fallback:
                print("Browser mode failed, falling back to CLI mode…")
                cli_err = _run_cli_mode()
                if cli_err:
                    return cli_err
                return (
                    f"{err}\n\n"
                    f"💡 Falling back to CLI mode succeeded — see output above.\n"
                    f"   To always use CLI mode: /hermes-snapshot-analytics --mode cli"
                )
            return err
        return _format_browser_response(msgs)

    elif mode == "both":
        cli_err = _run_cli_mode()
        err, msgs = _run_browser_mode(server_port, dashboard_port)
        if err:
            return f"CLI output shown above.\n\nBrowser mode failed:\n{err}"
        browser_resp = _format_browser_response(msgs)
        if cli_err:
            return f"CLI mode failed ({cli_err})\n\n{browser_resp}"
        return f"CLI metrics printed above.\n\n{browser_resp}"

    return f"❌ Unknown mode: {mode}"


def _format_browser_response(msgs: list[str]) -> str:
    """Build a friendly response string from _run_browser_mode output."""
    url = msgs[-1] if msgs and msgs[-1].startswith("http") else ""
    notices = [m for m in msgs[:-1] if m]

    lines = [
        "✅ **Hermes Analytics is ready!**",
        "",
        f"📊 **Your dashboard:** {url}",
    ]
    for n in notices:
        lines.insert(2, f"ℹ️ {n}")
    lines.extend([
        "",
        "Use the **🛑 Shutdown Analytics** button in the dashboard sidebar to stop all analytics processes.",
        "Closing the browser tab will NOT stop the services — only the button does.",
    ])
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# Plugin registration
# ──────────────────────────────────────────────────────────────────────

def register(ctx):
    """Register the /hermes-snapshot-analytics slash command."""
    from . import schemas

    ctx.register_command(
        "hermes-snapshot-analytics",
        handler=_handle_snapshot_analytics,
        description="Start Hermes Analytics: collect snapshot, print metrics",
    )

    logger.info("Hermes Analytics plugin registered — /hermes-snapshot-analytics available")
