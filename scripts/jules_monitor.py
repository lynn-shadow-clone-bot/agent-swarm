#!/usr/bin/env python3
"""
Jules Session Monitor - Checks for completed sessions and notifies via Telegram.
Called by cron every minute.
"""
import json
import os
import subprocess
import sys
from datetime import datetime

# Config
SESSIONS_FILE = os.path.expanduser("~/.openclaw/workspace/skills/agent-swarm/.jules_sessions")
NOTIFICATION_LOG = os.path.expanduser("~/.openclaw/workspace/skills/agent-swarm/logs/jules_monitor.log")
TELEGRAM_CHAT_ID = "8449755183"  # Kai's Telegram ID

def log(message):
    """Log to file and stdout."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    # Ensure log dir exists
    log_dir = os.path.dirname(NOTIFICATION_LOG)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    with open(NOTIFICATION_LOG, "a") as f:
        f.write(log_line + "\n")

def load_sessions():
    """Load tracked sessions from file."""
    if not os.path.exists(SESSIONS_FILE):
        return {}
    
    try:
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading sessions: {e}")
        return {}

def save_sessions(sessions):
    """Save sessions to file."""
    try:
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        log(f"Error saving sessions: {e}")

def get_jules_status(session_id):
    """Get status of a Jules session via CLI."""
    try:
        result = subprocess.run(
            ["jules", "remote", "list", "--session"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            log(f"Error running jules command: {result.stderr}")
            return None
        
        # Parse output for session status
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if session_id in line:
                # Format: ID  Description  Repo  Last active  Status
                # Extract status (last column)
                parts = line.split()
                if len(parts) >= 5:
                    status = parts[-1]
                    return status
        
        return None  # Session not found
        
    except subprocess.TimeoutExpired:
        log(f"Timeout checking session {session_id}")
        return None
    except Exception as e:
        log(f"Error checking session {session_id}: {e}")
        return None

def send_telegram_notification(session_id, session_info):
    """Send notification via Telegram (via OpenClaw message tool)."""
    repo = session_info.get("repo", "unknown")
    description = session_info.get("description", "No description")
    status = session_info.get("status", "Completed")
    
    message = f"""🎯 Jules Session FERTIG!

Session ID: {session_id}
Status: {status}
Repo: {repo}
Description: {description}

🔗 Review: https://jules.google.com/session/{session_id}

💻 PR erstellen:
```
cd ~/.openclaw/workspace/skills/agent-swarm
jules remote pull --session {session_id} --apply
```
"""
    
    # Write to notification directory for main agent to pick up
    notification_dir = "/tmp/jules_notifications"
    os.makedirs(notification_dir, exist_ok=True)
    
    notification_file = f"{notification_dir}/jules_notification_{session_id}.txt"
    with open(notification_file, "w") as f:
        f.write(message)
    
    log(f"Notification queued for session {session_id}: {notification_file}")
    
    # Also try to use openclaw notify if available
    try:
        subprocess.run(
            ["openclaw", "notify", "--channel", "telegram", "--user", TELEGRAM_CHAT_ID, "--message", message],
            capture_output=True,
            timeout=10
        )
        log(f"Direct notification sent for session {session_id}")
    except Exception as e:
        log(f"Direct notification not available (expected in cron): {e}")

def main():
    """Main monitoring loop."""
    log("=== Jules Session Monitor Check ===")
    
    sessions = load_sessions()
    
    if not sessions:
        log("No active sessions to monitor")
        return
    
    log(f"Monitoring {len(sessions)} session(s): {list(sessions.keys())}")
    
    completed_sessions = []
    
    for session_id, session_info in sessions.items():
        log(f"Checking session {session_id}...")
        
        status = get_jules_status(session_id)
        
        if status is None:
            log(f"  Session {session_id} not found in jules list, skipping")
            continue
        
        log(f"  Status: {status}")
        
        if status in ["Completed", "Failed", "Error", "Cancelled"]:
            log(f"  Session {session_id} finished with status: {status}")
            
            # Update session info with status
            session_info["status"] = status
            
            # Send notification
            send_telegram_notification(session_id, session_info)
            
            # Mark for removal
            completed_sessions.append(session_id)
        else:
            log(f"  Session {session_id} still running...")
    
    # Remove completed sessions from tracking
    for session_id in completed_sessions:
        del sessions[session_id]
        log(f"  Removed {session_id} from tracking")
    
    save_sessions(sessions)
    
    if completed_sessions:
        log(f"Notified about {len(completed_sessions)} completed session(s)")
    else:
        log("No sessions completed this check")

if __name__ == "__main__":
    main()
