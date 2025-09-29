#!/usr/bin/env python3
"""
Syncthing Notification Monitor
Auto-detects Syncthing config and sends macOS notifications for errors/conflicts

Git repo for updates: github.com/timurmuh/syncthing-notifier
"""

import json
import urllib.request
import urllib.error
import subprocess
import time
import sys
import signal
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION = "1.0.0"

# Paths
SYNCTHING_CONFIG_PATH = Path.home() / "Library/Application Support/Syncthing/config.xml"
USER_CONFIG_DIR = Path.home() / ".config/syncthing-notifier"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.json"
LAST_EVENT_ID_PATH = USER_CONFIG_DIR / "last_event_id"

# Default user preferences (syncs via Git)
DEFAULT_USER_CONFIG = {
    "version": VERSION,
    "notify_on": {
        "folder_errors": True,
        "item_errors": True,
        "conflicts": True
    },
    "notification_sound": True,
    "check_interval_on_error": 5
}

class SyncthingConfig:
    """Parse Syncthing's config.xml to get URL and API key"""
    
    def __init__(self):
        self.url = None
        self.api_key = None
        self._parse()
    
    def _parse(self):
        """Parse config.xml and extract GUI settings"""
        if not SYNCTHING_CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"Syncthing config not found at {SYNCTHING_CONFIG_PATH}\n"
                "Is Syncthing installed and running?"
            )
        
        try:
            tree = ET.parse(SYNCTHING_CONFIG_PATH)
            root = tree.getroot()
            
            # Find GUI element
            gui = root.find('gui')
            if gui is None:
                raise ValueError("No <gui> element found in config.xml")
            
            # Get address
            address_elem = gui.find('address')
            if address_elem is not None:
                address = address_elem.text
                # Add http:// if not present
                if address and not address.startswith('http'):
                    address = f'http://{address}'
                self.url = address
            
            # Get API key
            apikey_elem = gui.find('apikey')
            if apikey_elem is not None:
                self.api_key = apikey_elem.text
            
            if not self.url or not self.api_key:
                raise ValueError("Could not find URL or API key in config.xml")
                
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse config.xml: {e}")
    
    def __repr__(self):
        return f"SyncthingConfig(url={self.url}, api_key={'***' + self.api_key[-4:] if self.api_key else None})"

def load_user_config():
    """Load user preferences from ~/.config/syncthing-notifier/config.json"""
    if USER_CONFIG_PATH.exists():
        try:
            with open(USER_CONFIG_PATH) as f:
                config = json.load(f)
                # Merge with defaults to handle version updates
                merged = DEFAULT_USER_CONFIG.copy()
                merged.update(config)
                return merged
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
            return DEFAULT_USER_CONFIG
    else:
        # Create default config
        USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIG_PATH, 'w') as f:
            json.dump(DEFAULT_USER_CONFIG, f, indent=2)
        print(f"Created default config at: {USER_CONFIG_PATH}")
        return DEFAULT_USER_CONFIG

def save_user_config(config):
    """Save user preferences"""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def send_notification(title, message, subtitle="", sound=True):
    """Send macOS notification using osascript"""
    # Escape quotes in strings
    message = message.replace('"', '\\"')
    title = title.replace('"', '\\"')
    subtitle = subtitle.replace('"', '\\"')
    
    if subtitle:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
    else:
        script = f'display notification "{message}" with title "{title}"'
    
    if sound:
        script += ' sound name "default"'
    
    try:
        subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        pass  # Silently fail if notification doesn't work

def make_request(url, api_key, timeout=70):
    """Make authenticated request to Syncthing API"""
    req = urllib.request.Request(url)
    req.add_header('X-API-Key', api_key)
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.URLError:
        return None
    except Exception:
        return None

def load_last_event_id():
    """Load the last processed event ID from disk"""
    if LAST_EVENT_ID_PATH.exists():
        try:
            with open(LAST_EVENT_ID_PATH) as f:
                return int(f.read().strip())
        except (ValueError, FileNotFoundError):
            return 0
    return 0

def save_last_event_id(event_id):
    """Save the last processed event ID to disk"""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LAST_EVENT_ID_PATH, 'w') as f:
        f.write(str(event_id))

def monitor_events(syncthing_config, user_config):
    """Monitor Syncthing events and send notifications"""
    base_url = syncthing_config.url
    api_key = syncthing_config.api_key

    last_event_id = load_last_event_id()
    print(f"Monitoring Syncthing at {base_url}")
    print(f"Config: {USER_CONFIG_PATH}")
    print(f"Resuming from event ID: {last_event_id}")
    print("Waiting for events...")
    
    # Event filters we care about
    events_filter = "FolderErrors,ItemFinished,StateChanged"
    sound = user_config.get('notification_sound', True)
    
    while True:
        try:
            # Long polling - blocks until events arrive or timeout
            url = f"{base_url}/rest/events?since={last_event_id}&events={events_filter}&timeout=60"
            events = make_request(url, api_key, timeout=70)
            
            if events is None:
                # Connection error, wait and retry
                time.sleep(user_config.get('check_interval_on_error', 5))
                continue
            
            if not events:
                continue
            
            # Process events with deduplication within this batch
            seen_notifications = set()

            for event in events:
                last_event_id = event['id']
                event_type = event['type']
                data = event.get('data', {})
                
                # Handle FolderErrors
                if event_type == 'FolderErrors' and user_config['notify_on']['folder_errors']:
                    folder = data.get('folder', 'Unknown')
                    errors = data.get('errors', [])

                    if errors:
                        error_count = len(errors)
                        first_error = errors[0].get('error', 'Unknown error')
                        # Truncate long error messages
                        if len(first_error) > 100:
                            first_error = first_error[:97] + '...'

                        # Create deduplication key
                        dedup_key = ('FolderError', folder, first_error)
                        if dedup_key not in seen_notifications:
                            seen_notifications.add(dedup_key)
                            send_notification(
                                "Syncthing Folder Error",
                                first_error,
                                f"Folder: {folder} ({error_count} error(s))",
                                sound
                            )
                            print(f"[FolderError] {folder}: {first_error}")
                
                # Handle ItemFinished with errors
                elif event_type == 'ItemFinished' and user_config['notify_on']['item_errors']:
                    error = data.get('error')
                    if error:
                        item = data.get('item', 'Unknown')
                        folder = data.get('folder', 'Unknown')

                        # Truncate long paths
                        item_name = Path(item).name
                        if len(item_name) > 50:
                            item_name = item_name[:47] + '...'

                        # Create deduplication key
                        dedup_key = ('ItemError', folder, item, error)
                        if dedup_key not in seen_notifications:
                            seen_notifications.add(dedup_key)
                            send_notification(
                                "Syncthing Sync Error",
                                error[:100] if len(error) > 100 else error,
                                f"{item_name} in {folder}",
                                sound
                            )
                            print(f"[ItemError] {item}: {error}")
                    
                    # Check for conflicts
                    if user_config['notify_on']['conflicts']:
                        item = data.get('item', '')
                        if '.sync-conflict-' in item:
                            folder = data.get('folder', 'Unknown')
                            item_name = Path(item).name

                            # Create deduplication key
                            dedup_key = ('Conflict', folder, item)
                            if dedup_key not in seen_notifications:
                                seen_notifications.add(dedup_key)
                                send_notification(
                                    "Syncthing Conflict",
                                    f"{item_name}",
                                    f"Folder: {folder}",
                                    sound
                                )
                                print(f"[Conflict] {item}")
        
            # Save the last event ID after processing all events
            if events:
                save_last_event_id(last_event_id)

        except KeyboardInterrupt:
            print("\nStopping monitor...")
            # Save current position before exiting
            save_last_event_id(last_event_id)
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(5)

def check_for_updates():
    """Check if there's a newer version available (optional)"""
    # This could check GitHub releases
    # For now, just print current version
    print(f"Syncthing Notifier v{VERSION}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\nReceived signal {signum}, stopping...")
    sys.exit(0)

def main():
    """Main entry point"""
    print(f"Syncthing Notifier v{VERSION}")
    print("-" * 40)

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Load Syncthing config (auto-detect)
        syncthing_config = SyncthingConfig()
        print(f"✓ Found Syncthing: {syncthing_config.url}")
        print(f"✓ API Key: ***{syncthing_config.api_key[-4:] if syncthing_config.api_key else 'None'}")
        
        # Load user preferences
        user_config = load_user_config()
        print(f"✓ User config: {USER_CONFIG_PATH}")
        
        # Test notification
        send_notification(
            "Syncthing Monitor Started",
            f"Monitoring {syncthing_config.url}",
            sound=user_config.get('notification_sound', True)
        )
        
        print("-" * 40)
        
        # Start monitoring
        monitor_events(syncthing_config, user_config)
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Syncthing is installed and has been run at least once.")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
