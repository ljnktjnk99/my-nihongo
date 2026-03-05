#!/bin/bash
# NihonGo Meeting - Quick Setup Script for macOS
# Run: bash scripts/setup.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_NAME="com.nihongo.watcher.plist"
PLIST_SRC="$PROJECT_DIR/scripts/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  NihonGo Meeting - Setup                     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "  Python 3 not found. Install: brew install python3"
    exit 1
fi
echo "  Python 3: $(python3 --version)"

if ! command -v git &> /dev/null; then
    echo "  Git not found. Install: xcode-select --install"
    exit 1
fi
echo "  Git: $(git --version | head -1)"

if ! command -v claude &> /dev/null; then
    echo "  Claude Code CLI not found. Install it first."
    echo "  https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi
echo "  Claude Code CLI: OK"

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv "$PROJECT_DIR/venv"
echo "  Virtual environment ready"

# Create directories
echo ""
echo "Creating directories..."
mkdir -p "$PROJECT_DIR/Meeting"
mkdir -p "$PROJECT_DIR/data/meetings"
mkdir -p "$PROJECT_DIR/translations"
mkdir -p "$PROJECT_DIR/processor/logs"
echo "  Directories created"

# Initialize data
if [ ! -f "$PROJECT_DIR/data/index.json" ]; then
    echo '{"meetings":[],"last_updated":""}' > "$PROJECT_DIR/data/index.json"
    echo "  index.json initialized"
fi

# Setup LaunchAgent
echo ""
read -p "Auto-start watcher on login? (y/n): " AUTO_START

if [ "$AUTO_START" = "y" ]; then
    # Unload existing if any
    launchctl unload "$PLIST_DEST" 2>/dev/null || true

    cp "$PLIST_SRC" "$PLIST_DEST"
    launchctl load "$PLIST_DEST"
    echo "  Watcher installed and started."
    echo "  Log: tail -f $PROJECT_DIR/processor/logs/watcher.log"
else
    echo "  Skipped. You can start manually:"
    echo "  python $PROJECT_DIR/processor/watcher.py"
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Setup done!                                 ║"
echo "║                                              ║"
echo "║  Drop transcript files into Meeting/ folder  ║"
echo "║  The watcher will auto-process them.         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
