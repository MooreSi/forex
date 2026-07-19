#!/bin/bash
# Start MT5 Bridge
# Launches mt5_bridge.py under Wine Python so it can talk to the MT5 terminal.
# MetaTrader 5 must be running and logged in before starting the bridge.
#
# Configuration (config.yaml):
#   wine_bin       — path to the Wine binary
#   mt5_bottle_path — WINEPREFIX directory (default: ~/.wine_mt5)
#
# To set up from scratch or migrate from CrossOver: run setup_wine_bridge.sh

set -e

FOREX_DIR="$(cd "$(dirname "$0")" && pwd)"
BRIDGE_SCRIPT="$FOREX_DIR/mt5_bridge.py"
BRIDGE_PORT="${MT5_BRIDGE_PORT:-9000}"

# ── Read config.yaml from user data directory ────────────────────────────────

USER_CONFIG="$HOME/Library/Application Support/ForexTrader/config.yaml"

read_config() {
    python3 -c "
import sys, os
try:
    import yaml
    with open(os.path.expanduser('~/Library/Application Support/ForexTrader/config.yaml')) as f:
        c = yaml.safe_load(f)
    key = sys.argv[1]
    val = c.get(key, '')
    if val:
        print(os.path.expanduser(str(val)))
except Exception:
    pass
" "$1" 2>/dev/null
}

WINE_BIN_CFG=$(read_config "wine_bin")
WINE_PREFIX_CFG=$(read_config "mt5_bottle_path")
BRIDGE_BACKEND=$(python3 -c "
import os
try:
    import yaml
    with open(os.path.expanduser('~/Library/Application Support/ForexTrader/config.yaml')) as f:
        c = yaml.safe_load(f)
    print(c.get('bridge_backend', 'crossover'))
except Exception:
    print('crossover')
" 2>/dev/null)

# ── Find the best available Wine binary ──────────────────────────────────────

find_wine() {
    # 1. Use binary from config.yaml if it exists
    if [ -n "$WINE_BIN_CFG" ] && [ -f "$WINE_BIN_CFG" ]; then
        echo "$WINE_BIN_CFG"; return 0
    fi
    # 2. System Wine (Homebrew Intel or Apple Silicon)
    for p in /opt/homebrew/bin/wine /usr/local/bin/wine; do
        [ -f "$p" ] && { echo "$p"; return 0; }
    done
    command -v wine &>/dev/null && { which wine; return 0; }
    # 3. CrossOver (still installed on this machine)
    local cx="/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine"
    [ -f "$cx" ] && { echo "$cx"; return 0; }
    return 1
}

WINE_BIN=$(find_wine || true)
if [ -z "$WINE_BIN" ]; then
    echo "ERROR: No Wine installation found."
    echo ""
    echo "Options:"
    echo "  brew install --cask --no-quarantine wine-crossover"
    echo "  brew install --cask whisky"
    echo "  Or keep CrossOver installed and set wine_bin in config.yaml"
    read -p "Press Enter to exit..."
    exit 1
fi

# ── Resolve Wine prefix based on backend ────────────────────────────────────

CX_BOTTLE="$HOME/Library/Application Support/CrossOver/Bottles/MetaTrader 5"

if [ "$BRIDGE_BACKEND" = "crossover" ]; then
    WINE_PREFIX="$CX_BOTTLE"
    USE_CROSSOVER=1
    echo "  Backend: CrossOver"
else
    WINE_PREFIX="${WINE_PREFIX_CFG:-$HOME/.wine_mt5}"
    USE_CROSSOVER=0
    echo "  Backend: Wine (independent prefix)"
fi

if [ ! -d "$WINE_PREFIX" ]; then
    if [ "$USE_CROSSOVER" = "1" ]; then
        echo "ERROR: CrossOver bottle not found at:"
        echo "  $WINE_PREFIX"
        echo "Is CrossOver installed and has MetaTrader 5 been set up in it?"
    else
        echo "ERROR: Wine prefix not found at $WINE_PREFIX"
        echo "Run setup_wine_bridge.sh to migrate or set up the prefix."
    fi
    read -p "Press Enter to exit..."
    exit 1
fi

# ── Ensure bridge script exists ──────────────────────────────────────────────

if [ ! -f "$BRIDGE_SCRIPT" ]; then
    echo "ERROR: Bridge script not found at $BRIDGE_SCRIPT"
    echo "Run setup_wine_bridge.sh first."
    read -p "Press Enter to exit..."
    exit 1
fi

# ── Kill any existing bridge on the same port ────────────────────────────────

EXISTING=$(lsof -ti tcp:$BRIDGE_PORT 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
    echo "Stopping existing bridge on port $BRIDGE_PORT (PID $EXISTING)..."
    kill $EXISTING 2>/dev/null || true
    sleep 1
fi

# ── Convert macOS paths to Wine Z: paths ────────────────────────────────────
# Wine maps the macOS root filesystem as the Z: drive.

WIN_SCRIPT="Z:$(printf '%s' "$BRIDGE_SCRIPT" | sed 's/\//\\/g')"

# Credentials file lives in the user data dir; pass as a Z: path so the
# bridge (running inside Wine) can read it from the Mac filesystem.
MAC_CREDS="$HOME/Library/Application Support/ForexTrader/bridge_credentials.json"
WIN_CREDS="Z:$(printf '%s' "$MAC_CREDS" | sed 's/\//\\/g')"

# ── Launch MT5 terminal if not already running ───────────────────────────────

MT5_EXE="$WINE_PREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
if [ -f "$MT5_EXE" ]; then
    if ! pgrep -f "terminal64.exe" > /dev/null 2>&1; then
        echo "Launching MetaTrader 5 terminal..."
        WINEPREFIX="$WINE_PREFIX" WINEDEBUG=-all \
            "$WINE_BIN" "C:\\Program Files\\MetaTrader 5\\terminal64.exe" &
        echo "Waiting 10 seconds for MT5 to initialise..."
        sleep 10
    else
        echo "MetaTrader 5 is already running."
    fi
else
    echo "Note: MT5 terminal not found at expected path — ensure it is running."
fi

# ── Start the bridge ─────────────────────────────────────────────────────────

echo ""
echo "==============================="
echo "  MT5 Bridge"
echo "==============================="
echo "Wine:    $WINE_BIN"
echo "Prefix:  $WINE_PREFIX"
echo "Script:  $BRIDGE_SCRIPT"
echo "Port:    $BRIDGE_PORT"
echo ""
echo "Press Ctrl+C to stop."
echo ""

if [ "$USE_CROSSOVER" = "1" ]; then
    WINEPREFIX="$WINE_PREFIX" \
    CX_BOTTLE="$WINE_PREFIX" \
    CX_NO_BROWSER=1 \
    WINEDEBUG=-all \
    MT5_BRIDGE_PORT="$BRIDGE_PORT" \
    BRIDGE_CREDS_PATH="$WIN_CREDS" \
        "$WINE_BIN" "C:\\Python311\\python.exe" "$WIN_SCRIPT"
else
    WINEPREFIX="$WINE_PREFIX" \
    WINEDEBUG=-all \
    MT5_BRIDGE_PORT="$BRIDGE_PORT" \
    BRIDGE_CREDS_PATH="$WIN_CREDS" \
        "$WINE_BIN" "C:\\Python311\\python.exe" "$WIN_SCRIPT"
fi
