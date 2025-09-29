#!/bin/bash
# Installs syncthing-notifier as a LaunchAgent

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_PATH="$SCRIPT_DIR/syncthing-notifier.py"
PLIST_DEST="$HOME/Library/LaunchAgents/com.syncthing.notifier.plist"

echo "Syncthing Notifier - Installation"
echo "=================================="
echo ""

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: syncthing-notifier.py not found in $SCRIPT_DIR"
    exit 1
fi

# Make script executable
chmod +x "$SCRIPT_PATH"
echo "✓ Made script executable"

# Create LaunchAgent directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$HOME/Library/Logs"

# Create plist file
cat > "$PLIST_DEST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.syncthing.notifier</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$SCRIPT_PATH</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/syncthing-notifier.log</string>
    
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/syncthing-notifier.error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>5</integer>
</dict>
</plist>
EOF

echo "✓ Created LaunchAgent plist at $PLIST_DEST"

# Unload if already running
if launchctl list | grep -q "com.syncthing.notifier"; then
    echo "  (Unloading existing service)"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Load the agent
launchctl load "$PLIST_DEST"
echo "✓ Loaded and started service"

echo ""
echo "Installation complete!"
echo ""
echo "The service will now:"
echo "  - Run automatically at login"
echo "  - Monitor Syncthing for errors and conflicts"
echo "  - Send macOS notifications when issues occur"
echo ""
echo "Useful commands:"
echo "  View logs:    tail -f ~/Library/Logs/syncthing-notifier.log"
echo "  Stop:         launchctl unload ~/Library/LaunchAgents/com.syncthing.notifier.plist"
echo "  Start:        launchctl load ~/Library/LaunchAgents/com.syncthing.notifier.plist"
echo "  Uninstall:    ./uninstall.sh"
echo "  Config:       ~/.config/syncthing-notifier/config.json"
echo ""
