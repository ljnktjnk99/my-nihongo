#!/bin/bash
# NihonGo Meeting - Quick Setup Script for macOS
# Run: bash scripts/setup.sh

set -e
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  🎌 NihonGo Meeting - Setup                 ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install: brew install python3"
    exit 1
fi
echo "  ✅ Python 3: $(python3 --version)"

if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Install: xcode-select --install"
    exit 1
fi
echo "  ✅ Git: $(git --version | head -1)"

if ! command -v claude &> /dev/null; then
    echo "  ⚠️  Claude Code CLI not found. Bạn cần cài Claude Code CLI."
    echo "     Nếu đã cài rồi, kiểm tra PATH."
else
    echo "  ✅ Claude Code CLI: OK"
fi

# Create virtual environment
echo ""
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -q watchdog
echo "  ✅ Virtual environment ready"

# Create directories
echo ""
echo "📁 Creating directories..."
mkdir -p Meeting
mkdir -p data/meetings
mkdir -p processor/logs
echo "  ✅ Directories created"

# Initialize data
if [ ! -f data/index.json ]; then
    echo '{"meetings":[],"last_updated":""}' > data/index.json
    echo "  ✅ index.json initialized"
fi

# Setup LaunchAgent (optional)
echo ""
read -p "🔄 Tự động chạy watcher khi mở máy? (y/n): " AUTO_START

if [ "$AUTO_START" = "y" ]; then
    # Update plist with correct home dir
    sed "s|\$HOME|$HOME|g" scripts/com.nihongo.watcher.plist > ~/Library/LaunchAgents/com.nihongo.watcher.plist
    launchctl load ~/Library/LaunchAgents/com.nihongo.watcher.plist 2>/dev/null || true
    echo "  ✅ Watcher sẽ tự chạy khi mở máy"
    echo "  📋 Log: tail -f /tmp/nihongo-watcher.log"
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ Setup hoàn tất!                         ║"
echo "║                                              ║"
echo "║  Bước tiếp theo:                             ║"
echo "║  1. git add . && git commit -m 'setup'       ║"
echo "║  2. git push origin main                     ║"
echo "║  3. Bật GitHub Pages (Settings → Pages)      ║"
echo "║  4. Test: python processor/watcher.py        ║"
echo "║  5. Bỏ file .txt vào Meeting/                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
