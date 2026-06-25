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
NC='\033[0m' # No Color

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
info "Step 1/4: Checking Python and pip…"

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

# Find pip
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
info "Step 2/4: Installing Python dependencies…"

# Idempotency check
DEPS_OK=true
for pkg in flask streamlit plotly pytest; do
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
# Step 3: Userend config
# ──────────────────────────────────────────────────
info "Step 3/4: Configuring userend client…"

CONFIG_FILE="$HOME/.hermes-analytics.conf"

if [ -f "$CONFIG_FILE" ]; then
    # Extract username from config
    USERNAME=$(grep -oP 'HERMES_ANALYTICS_USER=\K.*' "$CONFIG_FILE" 2>/dev/null || echo "unknown")
    success "Already configured for: $USERNAME ($CONFIG_FILE)"
else
    if [ -x "userend/install.sh" ]; then
        info "Running userend/install.sh for per-user config…"
        ./userend/install.sh && success "Userend configured" || {
            warn "userend/install.sh had issues — you can re-run it later."
        }
    else
        warn "userend/install.sh not found — skipping user config"
        warn "Run './userend/install.sh' manually to configure username and remote server."
    fi
fi

# ──────────────────────────────────────────────────
# Step 4: Initial collector run
# ──────────────────────────────────────────────────
info "Step 4/4: Running initial collector…"

if [ -f "snapshot_latest.json" ]; then
    success "snapshot_latest.json already exists — skipping initial collection"
else
    if [ -f "collector.py" ] || [ -f "userend/collector.py" ]; then
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
    else
        warn "collector.py not found — skipping initial collection"
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
echo "  Start the server:"
echo "    $PYTHON server.py &"
echo ""
echo "  Start the dashboard:"
echo "    streamlit run dashboard.py"
echo ""
echo "  Open in browser:"
echo "    http://localhost:8501"
echo ""
echo "  Run collector again:"
echo "    $PYTHON collector.py"
echo ""
echo "================================================"
echo ""
