# Syncthing Notification Monitor for macOS

Get instant macOS notifications for Syncthing errors, conflicts, and sync issues. No manual configuration needed - automatically detects your Syncthing setup.

## Features

- ✅ **Zero-config**: Auto-detects Syncthing URL and API key
- 🔔 **Native notifications**: Instant macOS notifications for problems
- 🪶 **Lightweight**: 10-15MB RAM, near-zero CPU when idle
- 🔄 **Auto-start**: Runs at login via LaunchAgent
- ⚙️ **Git-syncable**: Version-controlled config across your Macs
- 🐍 **No dependencies**: Pure Python 3 stdlib

## What Gets Monitored

- **Folder errors**: Permission issues, missing files, disk space problems
- **Sync failures**: Individual file sync errors
- **Conflicts**: When `.sync-conflict-*` files are created

## Quick Start

### 1. Clone and Install

```bash
# Clone this repo
git clone https://github.com/YOUR_USERNAME/syncthing-notifier.git
cd syncthing-notifier

# Install (creates LaunchAgent, starts service)
./install.sh
```

That's it! You'll get a notification confirming it's running.

### 2. Customize (Optional)

Edit `~/.config/syncthing-notifier/config.json`:

```json
{
  "notify_on": {
    "folder_errors": true,
    "item_errors": true,
    "conflicts": true
  },
  "notification_sound": true
}
```

Then restart:
```bash
launchctl unload ~/Library/LaunchAgents/com.syncthing.notifier.plist
launchctl load ~/Library/LaunchAgents/com.syncthing.notifier.plist
```

## Requirements

- macOS 11+ (Big Sur or later)
- Syncthing installed and configured (tested with [syncthing-macos](https://github.com/syncthing/syncthing-macos))
- Python 3 (pre-installed on macOS)

## How It Works

1. **Auto-detection**: Reads `~/Library/Application Support/Syncthing/config.xml` to get your Syncthing URL and API key
2. **Event monitoring**: Uses Syncthing's REST API with long polling (efficient, real-time)
3. **Smart notifications**: Filters events to show only errors, failures, and conflicts
4. **Background service**: Runs as a LaunchAgent, starts automatically at login

## Syncing Config Across Multiple Macs

### Option 1: Git (Recommended)

Your config lives in `~/.config/syncthing-notifier/` which you can version control:

```bash
# On first Mac
cd ~/.config
git init
git add syncthing-notifier/
git commit -m "Add syncthing-notifier config"
git remote add origin git@github.com:YOUR_USERNAME/dotfiles.git
git push -u origin main

# On other Macs
cd ~/.config
git clone git@github.com:YOUR_USERNAME/dotfiles.git temp
mv temp/syncthing-notifier .
rm -rf temp
```

### Option 2: Symlink to iCloud Drive

```bash
# Move to iCloud
mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/configs
mv ~/.config/syncthing-notifier ~/Library/Mobile\ Documents/com~apple~CloudDocs/configs/

# Symlink back
ln -s ~/Library/Mobile\ Documents/com~apple~CloudDocs/configs/syncthing-notifier ~/.config/syncthing-notifier
```

**Note**: The script and plist should be managed via Git (not iCloud), while config preferences can use either method.

## Updating

### Update the script:

```bash
cd ~/path/to/syncthing-notifier
git pull

# Restart service
launchctl unload ~/Library/LaunchAgents/com.syncthing.notifier.plist
launchctl load ~/Library/LaunchAgents/com.syncthing.notifier.plist
```

### Update your config:

```bash
# Edit preferences
nano ~/.config/syncthing-notifier/config.json

# Restart to apply
launchctl unload ~/Library/LaunchAgents/com.syncthing.notifier.plist
launchctl load ~/Library/LaunchAgents/com.syncthing.notifier.plist
```

## Management Commands

```bash
# Check status
launchctl list | grep syncthing.notifier

# View live logs
tail -f ~/Library/Logs/syncthing-notifier.log

# Manual test run (foreground)
./syncthing-notifier.py

# Stop service
launchctl unload ~/Library/LaunchAgents/com.syncthing.notifier.plist

# Start service
launchctl load ~/Library/LaunchAgents/com.syncthing.notifier.plist

# Restart (after updates)
launchctl unload ~/Library/LaunchAgents/com.syncthing.notifier.plist && \
launchctl load ~/Library/LaunchAgents/com.syncthing.notifier.plist
```

## Troubleshooting

### No notifications appearing?

1. Check System Settings → Notifications → Script Editor (allow notifications)
2. Test manually: `./syncthing-notifier.py`
3. Test notification system: `osascript -e 'display notification "Test" with title "Test"'`

### "Syncthing config not found" error?

- Verify Syncthing is installed: `ls ~/Library/Application\ Support/Syncthing/config.xml`
- Make sure Syncthing has been run at least once to create config

### Service won't start?

```bash
# Check error logs
cat ~/Library/Logs/syncthing-notifier.error.log

# Verify plist exists and has correct path
cat ~/Library/LaunchAgents/com.syncthing.notifier.plist | grep ProgramArguments -A 3
```

### Want to change Syncthing URL/API key?

The script reads these automatically from Syncthing's config. If you change them in Syncthing, just restart the notifier service.

## Uninstall

```bash
./uninstall.sh

# Or manually:
launchctl unload ~/Library/LaunchAgents/com.syncthing.notifier.plist
rm ~/Library/LaunchAgents/com.syncthing.notifier.plist

# Remove config (optional)
rm -rf ~/.config/syncthing-notifier

# Remove logs (optional)
rm ~/Library/Logs/syncthing-notifier*.log
```

## Configuration Reference

`~/.config/syncthing-notifier/config.json`:

```json
{
  "version": "1.0.0",
  "notify_on": {
    "folder_errors": true,      // Folder-level sync errors
    "item_errors": true,         // Individual file errors
    "conflicts": true            // Conflict file creation
  },
  "notification_sound": true,    // Play sound with notifications
  "check_interval_on_error": 5   // Seconds to wait before retry on connection error
}
```

## Architecture

```
syncthing-notifier.py
    │
    ├─→ Reads ~/Library/Application Support/Syncthing/config.xml
    │   (Gets URL and API key automatically)
    │
    ├─→ Reads ~/.config/syncthing-notifier/config.json
    │   (User preferences - what to notify)
    │
    ├─→ Connects to Syncthing REST API
    │   (Long polling on /rest/events)
    │
    └─→ Sends macOS notifications via osascript
        (Native notification center)
```

## Performance

- **Memory**: ~10-15MB RSS
- **CPU**: <0.1% average (long polling, not active polling)
- **Network**: Minimal (single persistent HTTP connection)
- **Battery impact**: Negligible

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test: `./syncthing-notifier.py`
5. Commit: `git commit -am 'Add feature'`
6. Push: `git push origin feature-name`
7. Create a Pull Request

## License

MIT License - feel free to use and modify

## Related Projects

- [syncthing/syncthing](https://github.com/syncthing/syncthing) - The main Syncthing project
- [syncthing/syncthing-macos](https://github.com/syncthing/syncthing-macos) - Official macOS app bundle
