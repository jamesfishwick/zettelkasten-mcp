#!/bin/bash
#
# Install the cluster detection LaunchAgent for automatic daily analysis.
# This script configures and installs the macOS LaunchAgent that runs
# cluster detection every day at 6am.
#
# Usage:
#   ./scripts/install-cluster-detection.sh          # Install
#   ./scripts/install-cluster-detection.sh --uninstall  # Uninstall
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.slipbox.cluster-detection.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

uninstall() {
    info "Uninstalling cluster detection LaunchAgent..."

    if launchctl list | grep -q "com.slipbox.cluster-detection"; then
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
    info "Installing cluster detection LaunchAgent..."

    # Check prerequisites
    if [ ! -f "$PLIST_SOURCE" ]; then
        error "Source plist not found: $PLIST_SOURCE"
    fi

    # Detect Python path
    if [ -f "$REPO_DIR/.venv/bin/python" ]; then
        PYTHON_PATH="$REPO_DIR/.venv/bin/python"
    elif command -v python3 &> /dev/null; then
        PYTHON_PATH="$(which python3)"
        warn "Using system Python: $PYTHON_PATH (recommend using venv)"
    else
        error "Python not found. Create a venv first: python -m venv .venv"
    fi

    # Verify the detect script exists
    DETECT_SCRIPT="$SCRIPT_DIR/detect_clusters.py"
    if [ ! -f "$DETECT_SCRIPT" ]; then
        error "Cluster detection script not found: $DETECT_SCRIPT"
    fi

    # Unload existing if present
    if launchctl list | grep -q "com.slipbox.cluster-detection"; then
        warn "Existing LaunchAgent found, unloading..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    # Create LaunchAgents directory if needed
    mkdir -p "$HOME/Library/LaunchAgents"

    # Generate plist with correct paths
    info "Generating plist with paths:"
    info "  Python: $PYTHON_PATH"
    info "  Script: $DETECT_SCRIPT"
    info "  Working dir: $REPO_DIR"

    cat > "$PLIST_DEST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.slipbox.cluster-detection</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$DETECT_SCRIPT</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/slipbox-clusters.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/slipbox-clusters.err</string>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
</dict>
</plist>
EOF

    # Load the LaunchAgent
    launchctl load "$PLIST_DEST"

    # Verify it loaded
    if launchctl list | grep -q "com.slipbox.cluster-detection"; then
        info "LaunchAgent loaded successfully"
    else
        error "Failed to load LaunchAgent"
    fi

    echo ""
    info "Installation complete!"
    echo ""
    echo "Cluster detection will run daily at 6:00 AM."
    echo ""
    echo "To test it now:"
    echo "  source .venv/bin/activate && python scripts/detect_clusters.py"
    echo ""
    echo "To check logs:"
    echo "  cat /tmp/slipbox-clusters.log"
    echo ""
    echo "To uninstall:"
    echo "  ./scripts/install-cluster-detection.sh --uninstall"
}

# Main
case "${1:-}" in
    --uninstall|-u)
        uninstall
        ;;
    --help|-h)
        echo "Usage: $0 [--uninstall]"
        echo ""
        echo "Install or uninstall the cluster detection LaunchAgent."
        echo "The LaunchAgent runs cluster analysis daily at 6am."
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
