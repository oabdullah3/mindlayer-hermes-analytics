#!/usr/bin/env bash
# Hermes Analytics — one-command setup
# Usage: ./install.sh
# Idempotent — safe to re-run multiple times.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

echo ""
echo "================================================"
echo "  Hermes Analytics Installer"
echo "================================================"
echo ""

# ──────────────────────────────────────────────────
# Step 1: Python & pip check
# ──────────────────────────────────────────────────
info "Step 1/5: Checking Python and pip…"

PYTHON=""
PIP=""

if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    error "Python 3 is required but not found. Install Python 3 first."
    exit 1
fi

$PYTHON --version 2>/dev/null || {
    error "Cannot determine Python version."
    exit 1
}

if command -v pip3 &>/dev/null; then
    PIP="pip3"
elif command -v pip &>/dev/null; then
    PIP="pip"
else
    error "pip is required. Install Python 3 and pip first."
    exit 1
fi

success "Python: $($PYTHON --version 2>&1) | pip: $PIP"

# ──────────────────────────────────────────────────
# Step 2: Python dependencies
# ──────────────────────────────────────────────────
info "Step 2/5: Installing Python dependencies…"

DEPS_OK=true
for pkg in flask streamlit plotly; do
    if ! $PYTHON -c "import $pkg" 2>/dev/null; then
        DEPS_OK=false
        break
    fi
done

if $DEPS_OK; then
    success "Python dependencies already installed"
else
    info "Installing from requirements.txt…"
    $PIP install -r requirements.txt && success "Dependencies installed" || {
        warn "pip install had issues — check output above. Continuing anyway."
    }
fi

# ──────────────────────────────────────────────────
# Step 3: Plugin symlink
# ──────────────────────────────────────────────────
info "Step 3/5: Installing Hermes plugin…"

HERMES_PLUGINS="$HOME/.hermes/plugins"
PLUGIN_LINK="$HERMES_PLUGINS/hermes-analytics"

if [ -L "$PLUGIN_LINK" ]; then
    CURRENT_TARGET=$(readlink "$PLUGIN_LINK")
    if [ "$CURRENT_TARGET" = "$SCRIPT_DIR" ]; then
        success "Plugin symlink already points to repo root"
    else
        warn "Plugin symlink exists but points to $CURRENT_TARGET — updating"
        rm -f "$PLUGIN_LINK"
        mkdir -p "$HERMES_PLUGINS"
        ln -sf "$SCRIPT_DIR" "$PLUGIN_LINK"
        success "Plugin symlink updated"
    fi
else
    mkdir -p "$HERMES_PLUGINS"
    ln -sf "$SCRIPT_DIR" "$PLUGIN_LINK"
    success "Plugin symlink created: ~/.hermes/plugins/hermes-analytics -> $(pwd)"
fi

# ──────────────────────────────────────────────────
# Step 4: User config (env vars only)
# ──────────────────────────────────────────────────
info "Step 4/5: Configuration (environment variables)…"

CONFIG_FILE="$HOME/.hermes-analytics.conf"
if [ -f "$CONFIG_FILE" ]; then
    warn "Old config file found at $CONFIG_FILE — it is no longer used."
    info "Configuration is now done via environment variables:"
    echo "  HERMES_ANALYTICS_USER   — your username for dashboards (default: \$USER)"
    echo "  HERMES_ANALYTICS_REMOTE — remote server URL (default: not set)"
    echo ""
    echo "  You can safely delete $CONFIG_FILE if you've migrated to env vars."
else
    success "No old config file — using env vars:"
    USERNAME="${HERMES_ANALYTICS_USER:-${USER:-$(uname -n)}}"
    echo "  HERMES_ANALYTICS_USER = $USERNAME"
    if [ -n "${HERMES_ANALYTICS_REMOTE:-}" ]; then
        echo "  HERMES_ANALYTICS_REMOTE = $HERMES_ANALYTICS_REMOTE"
    else
        echo "  HERMES_ANALYTICS_REMOTE = (not set - remote push disabled)"
    fi
fi

# ──────────────────────────────────────────────────
# Step 5: Initial collector run
# ──────────────────────────────────────────────────
info "Step 5/5: Running initial collector…"

if [ -f "snapshot_latest.json" ]; then
    success "snapshot_latest.json already exists — skipping initial collection"
else
    info "Running collector (this may take a moment)…"
    if $PYTHON collector.py 2>&1; then
        success "Initial snapshot generated"
        if [ -f "snapshot_latest.json" ]; then
            SESSIONS=$($PYTHON -c "import json; d=json.load(open('snapshot_latest.json')); print(len(d.get('sessions',[])))" 2>/dev/null || echo "?")
            success "Collected $SESSIONS sessions"
        fi
    else
        warn "Collector had issues — you can re-run it later with: $PYTHON collector.py"
    fi
fi

# ──────────────────────────────────────────────────
# Done — print summary
# ──────────────────────────────────────────────────
echo ""
echo "================================================"
echo "  Installation Complete!"
echo "================================================"
echo ""
echo "  Use the slash command inside Hermes:"
echo "    /hermes-snapshot-analytics"
echo ""
echo "  Or run components manually:"
echo ""
echo "    $PYTHON server.py &"
echo "    streamlit run dashboard.py"
echo ""
echo "  Collector only:"
echo "    $PYTHON collector.py"
echo ""
echo "================================================"
echo ""
