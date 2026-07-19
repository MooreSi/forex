#!/bin/bash
# setup_wine_bridge.sh — One-time setup for the MT5 Wine bridge
#
# What this script does:
#   1. Detects an available Wine binary (CrossOver, Homebrew, etc.)
#   2. Migrates the existing CrossOver MT5 bottle to ~/.wine_mt5
#      — OR sets up a fresh Wine prefix if no CrossOver bottle exists
#   3. Verifies that Python 3.11 and MetaTrader5 are available in the prefix
#   4. Ensures bridge_credentials.json and mt5_bridge.py are in this folder
#   5. Updates config.yaml with the new prefix path
#
# Run once after first install, or when setting up a new machine.
# Safe to re-run — all steps are idempotent.

set -e

FOREX_DIR="$(cd "$(dirname "$0")" && pwd)"
WINE_PREFIX="$HOME/.wine_mt5"
CX_BOTTLE="$HOME/Library/Application Support/CrossOver/Bottles/MetaTrader 5"
CX_WINE="/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine"
BRIDGE_SCRIPT="$FOREX_DIR/mt5_bridge.py"
CREDS_FILE="$FOREX_DIR/bridge_credentials.json"

echo "======================================="
echo "  MT5 Bridge — Wine Setup"
echo "======================================="
echo ""

# ── Step 1: Find Wine binary ─────────────────────────────────────────────────

echo "[ 1/5 ] Finding Wine binary..."

find_wine() {
    # Config-specified binary (read from user data directory)
    local cfg_wine
    cfg_wine=$(python3 -c "
import os, sys
try:
    import yaml
    cfg_path = os.path.expanduser('~/Library/Application Support/ForexTrader/config.yaml')
    with open(cfg_path) as f:
        c = yaml.safe_load(f)
    v = c.get('wine_bin', '')
    if v: print(os.path.expanduser(str(v)))
except Exception:
    pass
" 2>/dev/null)
    [ -n "$cfg_wine" ] && [ -f "$cfg_wine" ] && { echo "$cfg_wine"; return 0; }

    # Homebrew (Apple Silicon or Intel)
    for p in /opt/homebrew/bin/wine /usr/local/bin/wine; do
        [ -f "$p" ] && { echo "$p"; return 0; }
    done
    command -v wine &>/dev/null && { which wine; return 0; }

    # CrossOver (bundled wine — still works even if you later uninstall CrossOver)
    [ -f "$CX_WINE" ] && { echo "$CX_WINE"; return 0; }

    return 1
}

WINE_BIN=$(find_wine || true)
if [ -z "$WINE_BIN" ]; then
    echo ""
    echo "ERROR: No Wine installation found."
    echo ""
    echo "Install one of the following, then re-run this script:"
    echo "  Homebrew Wine:  brew install --cask --no-quarantine wine-crossover"
    echo "  Whisky (free):  brew install --cask whisky"
    echo "                  then open Whisky once, then locate its wine binary."
    echo "  Or reinstall CrossOver if you had it before."
    echo ""
    exit 1
fi

echo "  Wine binary: $WINE_BIN"

# ── Step 2: Set up Wine prefix ───────────────────────────────────────────────

echo ""
echo "[ 2/5 ] Setting up Wine prefix at $WINE_PREFIX..."

if [ -d "$WINE_PREFIX" ]; then
    echo "  Wine prefix already exists — skipping migration."

elif [ -d "$CX_BOTTLE" ]; then
    echo "  Migrating CrossOver bottle (this copies ~500 MB, may take a minute)..."
    rsync -a --progress \
        --exclude="cxbottle.conf" \
        --exclude="cxassoc.conf" \
        --exclude="cxmenu.conf" \
        --exclude="desktopdata" \
        --exclude="windata" \
        "$CX_BOTTLE/" "$WINE_PREFIX/"
    echo "  Migration complete."

else
    echo "  No CrossOver bottle found — creating a fresh Wine prefix."
    echo "  NOTE: You will need to install Python 3.11 and MetaTrader5 manually."
    echo "        See the README for instructions."
    WINEPREFIX="$WINE_PREFIX" WINEDEBUG=-all "$WINE_BIN" wineboot --init 2>/dev/null || true
    echo "  Fresh prefix created."
fi

# ── Step 3: Verify and install Python 3.11 + MetaTrader5 ────────────────────

echo ""
echo "[ 3/5 ] Verifying Wine Python and MetaTrader5 package..."

PYTHON_HOST_PATH="$WINE_PREFIX/drive_c/Python311/python.exe"

if [ ! -f "$PYTHON_HOST_PATH" ]; then
    echo ""
    echo "  Python 3.11 not found at C:\\Python311\\python.exe."
    echo "  Attempting automatic installation..."
    echo ""

    PY_VER="3.11.9"
    PY_URL="https://www.python.org/ftp/python/${PY_VER}/python-${PY_VER}-amd64.exe"
    PY_INSTALLER="/tmp/python-${PY_VER}-amd64.exe"

    if [ ! -f "$PY_INSTALLER" ]; then
        echo "  Downloading Python ${PY_VER} (~25 MB)..."
        if ! curl -fL --progress-bar "$PY_URL" -o "$PY_INSTALLER"; then
            echo ""
            echo "  ERROR: Download failed. Check your internet connection."
            echo "  To install manually, download Python 3.11 from python.org"
            echo "  and run it inside your Wine prefix."
            exit 1
        fi
        echo "  Download complete."
    else
        echo "  Installer already cached at $PY_INSTALLER"
    fi

    echo "  Installing Python 3.11 inside Wine prefix (1-3 minutes)..."
    PY_WIN_PATH="Z:$(echo "$PY_INSTALLER" | sed 's|/|\\|g')"
    WINEPREFIX="$WINE_PREFIX" WINEDEBUG=-all "$WINE_BIN" \
        "$PY_WIN_PATH" /quiet InstallAllUsers=0 \
        TargetDir="C:\\Python311" Include_pip=1 Shortcuts=0 PrependPath=0 \
        2>/dev/null || true

    # Give the installer a moment to finalise
    sleep 3

    if [ -f "$PYTHON_HOST_PATH" ]; then
        echo "  Python 3.11 installed successfully."
    else
        echo ""
        echo "  WARNING: Python 3.11 installation may have failed."
        echo "  Try installing it manually via CrossOver:"
        echo "    1. Open CrossOver → MetaTrader 5 bottle"
        echo "    2. Run: python-${PY_VER}-amd64.exe /quiet TargetDir=C:\\Python311"
        echo "  Then re-run this script."
    fi
fi

MT5_CHECK=$(WINEPREFIX="$WINE_PREFIX" WINEDEBUG=-all "$WINE_BIN" \
    "C:\\Python311\\python.exe" -c \
    "import MetaTrader5; print('OK')" 2>/dev/null || true)

if [ "$MT5_CHECK" = "OK" ]; then
    echo "  Python 3.11 + MetaTrader5: OK"
else
    PY_CHECK=$(WINEPREFIX="$WINE_PREFIX" WINEDEBUG=-all "$WINE_BIN" \
        "C:\\Python311\\python.exe" --version 2>/dev/null || true)
    if echo "$PY_CHECK" | grep -q "Python 3.11"; then
        echo "  Python 3.11 found. Installing MetaTrader5 package..."
        WINEPREFIX="$WINE_PREFIX" WINEDEBUG=-all "$WINE_BIN" \
            "C:\\Python311\\python.exe" -m pip install MetaTrader5 2>&1 || true
        echo "  MetaTrader5 installation attempted."
    else
        echo "  WARNING: Python 3.11 not available — MetaTrader5 cannot be installed."
        echo "  Verify Python is installed at C:\\Python311\\ in the Wine prefix."
    fi
fi

# ── Step 4: Ensure bridge files are in the FOREX folder ─────────────────────

echo ""
echo "[ 4/5 ] Checking bridge files in FOREX folder..."

# Bridge script
if [ ! -f "$BRIDGE_SCRIPT" ]; then
    # Try to copy from the migrated prefix's drive_c
    OLD_BRIDGE="$WINE_PREFIX/drive_c/mt5_bridge.py"
    if [ -f "$OLD_BRIDGE" ]; then
        cp "$OLD_BRIDGE" "$BRIDGE_SCRIPT"
        echo "  Copied mt5_bridge.py from Wine prefix."
    elif [ -f "$CX_BOTTLE/drive_c/mt5_bridge.py" ]; then
        cp "$CX_BOTTLE/drive_c/mt5_bridge.py" "$BRIDGE_SCRIPT"
        echo "  Copied mt5_bridge.py from CrossOver bottle."
    else
        echo "  WARNING: mt5_bridge.py not found. The bridge script should be"
        echo "  at: $BRIDGE_SCRIPT"
    fi
else
    echo "  mt5_bridge.py: OK"
fi

# Credentials
if [ ! -f "$CREDS_FILE" ]; then
    for src in \
        "$WINE_PREFIX/drive_c/bridge_credentials.json" \
        "$CX_BOTTLE/drive_c/bridge_credentials.json"; do
        if [ -f "$src" ]; then
            cp "$src" "$CREDS_FILE"
            echo "  Copied bridge_credentials.json from $(dirname $src)."
            break
        fi
    done
    if [ ! -f "$CREDS_FILE" ]; then
        echo "  NOTE: bridge_credentials.json not found."
        echo "  Enter your MT5 credentials in Settings > MT5 / Bridge and save."
    fi
else
    echo "  bridge_credentials.json: OK"
fi

# ── Step 5: Update config.yaml ───────────────────────────────────────────────

echo ""
echo "[ 5/5 ] Updating config.yaml..."

python3 - <<PYEOF
import os, re

config_path = os.path.expanduser("~/Library/Application Support/ForexTrader/config.yaml")
wine_prefix = os.path.expanduser("$WINE_PREFIX")

try:
    with open(config_path) as f:
        content = f.read()

    # Update mt5_bottle_path
    content = re.sub(
        r'^mt5_bottle_path:.*$',
        f'mt5_bottle_path: {wine_prefix}',
        content,
        flags=re.MULTILINE,
    )

    with open(config_path, 'w') as f:
        f.write(content)

    print(f"  config.yaml updated: mt5_bottle_path -> {wine_prefix}")
except Exception as e:
    print(f"  WARNING: Could not update config.yaml: {e}")
    print(f"  Manually set mt5_bottle_path: {wine_prefix}")
PYEOF

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "======================================="
echo "  Setup complete."
echo "======================================="
echo ""
echo "To start the bridge:"
echo "  Double-click 'Start MT5 Bridge.command'"
echo "  (MetaTrader 5 will launch automatically if not already running.)"
echo ""
echo "To switch Wine binary (e.g. after installing Homebrew Wine):"
echo "  Edit ~/Library/Application Support/ForexTrader/config.yaml"
echo "  and set:  wine_bin: /opt/homebrew/bin/wine"
echo ""
