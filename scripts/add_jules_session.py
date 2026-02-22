#!/usr/bin/env python3
"""
Add a Jules session to the monitoring list.
Usage: python3 scripts/add_jules_session.py <session_id> <repo> <description>
"""
import json
import os
import sys
from datetime import datetime

SESSIONS_FILE = os.path.expanduser("~/.openclaw/workspace/skills/agent-swarm/.jules_sessions")

def add_session(session_id, repo, description):
    """Add a session to the tracking file."""
    # Load existing sessions
    sessions = {}
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                sessions = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing sessions: {e}")
            sessions = {}
    
    # Add new session
    sessions[session_id] = {
        "repo": repo,
        "description": description,
        "added_at": datetime.now().isoformat()
    }
    
    # Save back
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)
    
    print(f"✅ Added session {session_id} to monitoring")
    print(f"   Repo: {repo}")
    print(f"   Description: {description}")
    print(f"   File: {SESSIONS_FILE}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 scripts/add_jules_session.py <session_id> <repo> <description>")
        print("Example: python3 scripts/add_jules_session.py 123456789 \"lynn-shadow-clone-bot/agent-swarm\" \"Phase 4: Scalability\"")
        sys.exit(1)
    
    session_id = sys.argv[1]
    repo = sys.argv[2]
    description = sys.argv[3]
    
    add_session(session_id, repo, description)
