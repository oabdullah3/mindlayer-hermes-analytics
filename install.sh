#!/usr/bin/env bash
# Hermes Analytics — dev setup
# Usage: ./install.sh
# Symlinks the plugin into ~/.hermes/plugins/ and optionally runs the collector.
# Dependencies are auto-installed at runtime by the plugin itself — this script
# does NOT run pip install.

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
echo "  Hermes Analytics — Dev Setup"
echo "================================================"
echo ""

# ── Step 1: Python check ──
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    error "Python 3 is required but not found."
    exit 1
fi
success "Python: $($PYTHON --version 2>&1)"

# ── Step 2: Plugin symlink ──
info "Symlinking plugin into ~/.hermes/plugins/ …"

HERMES_PLUGINS="$HOME/.hermes/plugins"
PLUGIN_LINK="$HERMES_PLUGINS/hermes-analytics"

mkdir -p "$HERMES_PLUGINS"

if [ -L "$PLUGIN_LINK" ]; then
    CURRENT_TARGET=$(readlink "$PLUGIN_LINK")
    if [ "$CURRENT_TARGET" = "$SCRIPT_DIR" ]; then
        success "Plugin symlink already points here"
    else
        warn "Plugin symlink points to $CURRENT_TARGET — updating"
        rm -f "$PLUGIN_LINK"
        ln -sf "$SCRIPT_DIR" "$PLUGIN_LINK"
        success "Plugin symlink updated"
    fi
else
    ln -sf "$SCRIPT_DIR" "$PLUGIN_LINK"
    success "Plugin symlink created: ~/.hermes/plugins/hermes-analytics -> $(pwd)"
fi

# ── Step 3: Dependencies note ──
info "Dependencies are auto-installed at runtime by the plugin."
info "If you want to install them now for local dev:"
echo "  $PYTHON -m pip install -r requirements.txt"
echo "  $PYTHON -m pip install -r requirements-dev.txt  # includes pytest"

# ── Step 4: Initial collector run (optional) ──
if [ -f "snapshot_latest.json" ]; then
    success "snapshot_latest.json already exists — skipping initial collection"
else
    info "Running collector to seed snapshot_latest.json …"
    if $PYTHON collector.py 2>&1; then
        success "Initial snapshot generated"
        if [ -f "snapshot_latest.json" ]; then
            SESSIONS=$($PYTHON -c "import json; d=json.load(open('snapshot_latest.json')); print(len(d.get('sessions',[])))" 2>/dev/null || echo "?")
            success "Collected $SESSIONS sessions"
        fi
    else
        warn "Collector had issues — you can re-run it later: $PYTHON collector.py"
    fi
fi

# ── Done ──
echo ""
echo "================================================"
echo "  Dev Setup Complete!"
echo "================================================"
echo ""
echo "  In Hermes chat:"
echo "    /hermes-snapshot-analytics --mode browser"
echo ""
echo "  Or run components manually:"
echo "    $PYTHON server.py &"
echo "    streamlit run dashboard.py"
echo ""
echo "  Tests:"
echo "    $PYTHON -m pytest tests/ -v"
echo ""
echo "================================================"
echo ""
