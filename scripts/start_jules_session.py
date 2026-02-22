#!/usr/bin/env python3
"""
Start a Jules session and automatically add it to the monitoring list.
Usage: python3 scripts/start_jules_session.py --repo <repo> --session <description>
Example: python3 scripts/start_jules_session.py --repo lynn-shadow-clone-bot/agent-swarm --session "Phase 5: Security"
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime

SESSIONS_FILE = os.path.expanduser("~/.openclaw/workspace/skills/agent-swarm/.jules_sessions")

def log(message):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def add_session_to_tracking(session_id, repo, description):
    """Add session to the tracking file."""
    sessions = {}
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                sessions = json.load(f)
        except Exception as e:
            log(f"Warning: Could not load existing sessions: {e}")
            sessions = {}
    
    sessions[session_id] = {
        "repo": repo,
        "description": description,
        "added_at": datetime.now().isoformat()
    }
    
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)
    
    return True

def start_jules_session(repo, description):
    """Start a Jules session and return session ID."""
    log(f"Starting Jules session for {repo}...")
    log(f"Description: {description}")
    
    try:
        result = subprocess.run(
            ["jules", "remote", "new", "--repo", repo, "--session", description],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            log(f"Error starting Jules session: {result.stderr}")
            return None
        
        output = result.stdout
        log("Jules session created successfully!")
        print("\n" + "="*60)
        print(output)
        print("="*60 + "\n")
        
        # Parse session ID from output
        # Format: "ID: 1234567890123456789"
        id_match = re.search(r'ID:\s*(\d+)', output)
        if id_match:
            session_id = id_match.group(1)
            return session_id
        else:
            log("Warning: Could not parse session ID from output")
            return None
            
    except subprocess.TimeoutExpired:
        log("Timeout starting Jules session")
        return None
    except Exception as e:
        log(f"Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Start a Jules session and add to monitoring")
    parser.add_argument("--repo", required=True, help="Repository (e.g., lynn-shadow-clone-bot/agent-swarm)")
    parser.add_argument("--session", required=True, help="Session description/task")
    
    args = parser.parse_args()
    
    # Start Jules session
    session_id = start_jules_session(args.repo, args.session)
    
    if not session_id:
        log("Failed to start session or get session ID")
        sys.exit(1)
    
    # Add to tracking
    log(f"Adding session {session_id} to monitoring list...")
    if add_session_to_tracking(session_id, args.repo, args.session):
        log("✅ Session added to monitoring successfully!")
        log(f"   File: {SESSIONS_FILE}")
        log("")
        log("The cronjob will now check this session every minute.")
        log("You'll get a Telegram notification when it's completed.")
        log("")
        log(f"🔗 Monitor: https://jules.google.com/session/{session_id}")
    else:
        log("❌ Failed to add session to monitoring")
        sys.exit(1)

if __name__ == "__main__":
    main()
