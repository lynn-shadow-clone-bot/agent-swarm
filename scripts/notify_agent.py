#!/usr/bin/env python3
"""
Check for pending Jules notifications and send them via Telegram.
This script should be called regularly (e.g., via heartbeat or every 5 minutes).
"""
import os
import glob
import json
from datetime import datetime

NOTIFICATION_DIR = "/tmp/jules_notifications"
STATE_FILE = "/tmp/jules_notifier_state.json"

def get_pending_notifications():
    """Get all pending notification files."""
    if not os.path.exists(NOTIFICATION_DIR):
        return []
    
    pattern = f"{NOTIFICATION_DIR}/jules_notification_*.txt"
    files = glob.glob(pattern)
    
    # Load already-sent notifications
    sent = set()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                sent = set(state.get("sent", []))
        except:
            pass
    
    notifications = []
    for filepath in files:
        session_id = os.path.basename(filepath).replace("jules_notification_", "").replace(".txt", "")
        
        # Skip already sent
        if session_id in sent:
            continue
        
        try:
            with open(filepath, "r") as f:
                content = f.read()
                notifications.append({
                    "session_id": session_id,
                    "message": content,
                    "file": filepath
                })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return notifications

def mark_as_sent(session_id):
    """Mark a notification as sent."""
    sent = set()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                sent = set(state.get("sent", []))
        except:
            pass
    
    sent.add(session_id)
    
    with open(STATE_FILE, "w") as f:
        json.dump({"sent": list(sent)}, f)

def main():
    """Main entry point - returns notifications for the agent to send."""
    notifications = get_pending_notifications()
    
    if not notifications:
        return []
    
    result = []
    for n in notifications:
        result.append({
            "session_id": n["session_id"],
            "message": n["message"]
        })
        mark_as_sent(n["session_id"])
    
    return result

if __name__ == "__main__":
    # When called directly, just print notifications
    notifications = main()
    if notifications:
        for n in notifications:
            print(f"\n{'='*60}")
            print(f"SESSION: {n['session_id']}")
            print(f"{'='*60}")
            print(n['message'])
    else:
        print("No new notifications")
