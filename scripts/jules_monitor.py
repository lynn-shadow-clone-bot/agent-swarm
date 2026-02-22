#!/usr/bin/env python3
"""
Jules Session Monitor - Checks for completed sessions and notifies via Telegram.
Called by cron every minute.
"""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime

# Config
SESSIONS_FILE = os.path.expanduser("~/.openclaw/workspace/skills/agent-swarm/.jules_sessions")
NOTIFICATION_LOG = os.path.expanduser("~/.openclaw/workspace/skills/agent-swarm/logs/jules_monitor.log")
TELEGRAM_BOT_TOKEN = "8539437601:AAEgGVkcNTyNNse6hpa251sPUDyxaq53Xu8"
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

def send_telegram_message(message):
    """Send message via Telegram Bot API."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }).encode()
        
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get('ok'):
                return True
            else:
                log(f"Telegram API error: {result}")
                return False
    except Exception as e:
        log(f"Failed to send Telegram message: {e}")
        return False

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
    """Send notification via Telegram Bot API."""
    repo = session_info.get("repo", "unknown")
    description = session_info.get("description", "No description")
    status = session_info.get("status", "Completed")
    
    message = f"""🎯 <b>Jules Session FERTIG!</b>

<b>Session ID:</b> {session_id}
<b>Status:</b> {status}
<b>Repo:</b> {repo}
<b>Description:</b> {description}

🔗 <a href="https://jules.google.com/session/{session_id}">Review auf Jules</a>

💻 <b>PR erstellen:</b>
cd ~/.openclaw/workspace/skills/agent-swarm
jules remote pull --session {session_id} --apply
"""
    
    # Send directly via Telegram API
    if send_telegram_message(message):
        log(f"✅ Telegram notification sent for session {session_id}")
    else:
        log(f"❌ Failed to send Telegram notification for session {session_id}")
        # Fallback: write to file
        notification_dir = "/tmp/jules_notifications"
        os.makedirs(notification_dir, exist_ok=True)
        notification_file = f"{notification_dir}/jules_notification_{session_id}.txt"
        with open(notification_file, "w") as f:
            f.write(message)
        log(f"Notification saved to file: {notification_file}")

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
            
            # Send notification via Telegram
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
