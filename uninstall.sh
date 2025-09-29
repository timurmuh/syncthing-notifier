#!/bin/bash
# Uninstalls syncthing-notifier LaunchAgent

set -e

PLIST_PATH="$HOME/Library/LaunchAgents/com.syncthing.notifier.plist"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Syncthing Notifier - Uninstallation"
echo "===================================="
echo ""

if [ -f "$PLIST_PATH" ]; then
    # Stop the service
    if launchctl list | grep -q "com.syncthing.notifier"; then
        echo "Stopping service..."
        launchctl unload "$PLIST_PATH"
        echo "✓ Service stopped"
    fi
    
    # Remove plist
    rm "$PLIST_PATH"
    echo "✓ Removed LaunchAgent"
else
    echo "⚠ LaunchAgent not found (already uninstalled?)"
fi

echo ""
echo "Uninstallation complete!"
echo ""
echo "The following were NOT removed (remove manually if desired):"
echo "  Script:  $SCRIPT_DIR/syncthing-notifier.py"
echo "  Config:  ~/.config/syncthing-notifier/"
echo "  Logs:    ~/Library/Logs/syncthing-notifier*.log"
echo ""
echo "To reinstall: ./install.sh"
echo ""
