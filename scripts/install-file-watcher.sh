#!/bin/bash
#
# Install the file watcher LaunchAgent for automatic index rebuilding.
# This script configures and installs the macOS LaunchAgent that monitors
# the notes directory and rebuilds the index when files change.
#
# Usage:
#   ./scripts/install-file-watcher.sh              # Install
#   ./scripts/install-file-watcher.sh --uninstall  # Uninstall
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.slipbox.watcher.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$HOME/.local/share/mcp/slipbox"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

uninstall() {
    info "Uninstalling file watcher LaunchAgent..."

    if launchctl list 2>/dev/null | grep -q "com.slipbox.watcher"; then
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
        info "LaunchAgent unloaded"
    fi

    if [ -f "$PLIST_DEST" ]; then
        rm "$PLIST_DEST"
        info "Removed $PLIST_DEST"
    else
        warn "LaunchAgent plist not found at $PLIST_DEST"
    fi

    info "Uninstall complete"
    exit 0
}

install() {
    info "Installing file watcher LaunchAgent..."

    # Detect Python path
    if [ -f "$REPO_DIR/.venv/bin/python" ]; then
        PYTHON_PATH="$REPO_DIR/.venv/bin/python"
    elif command -v python3 &> /dev/null; then
        PYTHON_PATH="$(which python3)"
        warn "Using system Python: $PYTHON_PATH (recommend using venv)"
    else
        error "Python not found. Create a venv first: python -m venv .venv"
    fi

    # Verify the watcher script exists
    WATCHER_SCRIPT="$SCRIPT_DIR/watch_notes.py"
    if [ ! -f "$WATCHER_SCRIPT" ]; then
        error "File watcher script not found: $WATCHER_SCRIPT"
    fi

    # Check if watchdog is installed
    if ! "$PYTHON_PATH" -c "import watchdog" 2>/dev/null; then
        warn "watchdog not installed. Installing..."
        "$PYTHON_PATH" -m pip install watchdog || error "Failed to install watchdog"
    fi

    # Unload existing if present
    if launchctl list 2>/dev/null | grep -q "com.slipbox.watcher"; then
        warn "Existing LaunchAgent found, unloading..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    # Create directories
    mkdir -p "$HOME/Library/LaunchAgents"
    mkdir -p "$LOG_DIR"

    # Generate plist with correct paths
    info "Generating plist with paths:"
    info "  Python: $PYTHON_PATH"
    info "  Script: $WATCHER_SCRIPT"
    info "  Working dir: $REPO_DIR"
    info "  Log file: $LOG_DIR/watcher.log"

    cat > "$PLIST_DEST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.slipbox.watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$WATCHER_SCRIPT</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/watcher.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/watcher.log</string>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
</dict>
</plist>
EOF

    # Load the LaunchAgent
    launchctl load "$PLIST_DEST"

    # Give it a moment to start
    sleep 1

    # Verify it loaded
    if launchctl list 2>/dev/null | grep -q "com.slipbox.watcher"; then
        info "LaunchAgent loaded successfully"
    else
        error "Failed to load LaunchAgent. Check: cat $LOG_DIR/watcher.log"
    fi

    echo ""
    info "Installation complete!"
    echo ""
    echo "The file watcher is now running. It will:"
    echo "  - Start automatically on login"
    echo "  - Restart if it crashes"
    echo "  - Rebuild the index when .md files change"
    echo ""
    echo "To check status:"
    echo "  launchctl list | grep slipbox.watcher"
    echo ""
    echo "To view logs:"
    echo "  tail -f $LOG_DIR/watcher.log"
    echo ""
    echo "To uninstall:"
    echo "  ./scripts/install-file-watcher.sh --uninstall"
}

# Main
case "${1:-}" in
    --uninstall|-u)
        uninstall
        ;;
    --help|-h)
        echo "Usage: $0 [--uninstall]"
        echo ""
        echo "Install or uninstall the file watcher LaunchAgent."
        echo "The watcher monitors the notes directory and rebuilds the"
        echo "database index when markdown files are created, modified, or deleted."
        echo ""
        echo "Options:"
        echo "  --uninstall, -u  Remove the LaunchAgent"
        echo "  --help, -h       Show this help"
        exit 0
        ;;
    "")
        install
        ;;
    *)
        error "Unknown option: $1. Use --help for usage."
        ;;
esac
