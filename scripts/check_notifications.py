#!/usr/bin/env python3
"""
Send pending Jules notifications via Telegram.
Called by the main agent to flush notification queue.
"""
import os
import glob
from datetime import datetime

NOTIFICATION_DIR = "/tmp/jules_notifications"

def get_pending_notifications():
    """Get all pending notification files."""
    pattern = f"{NOTIFICATION_DIR}/jules_notification_*.txt"
    files = glob.glob(pattern)
    
    notifications = []
    for filepath in files:
        try:
            with open(filepath, "r") as f:
                content = f.read()
                session_id = os.path.basename(filepath).replace("jules_notification_", "").replace(".txt", "")
                notifications.append({
                    "session_id": session_id,
                    "message": content,
                    "file": filepath
                })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return notifications

def clear_notification(filepath):
    """Remove a notification file after sending."""
    try:
        os.remove(filepath)
        return True
    except Exception as e:
        print(f"Error removing {filepath}: {e}")
        return False

if __name__ == "__main__":
    notifications = get_pending_notifications()
    
    if notifications:
        print(f"Found {len(notifications)} pending notification(s)")
        for n in notifications:
            print(f"\n=== Notification for {n['session_id']} ===")
            print(n['message'])
            print("=" * 50)
    else:
        print("No pending notifications")
