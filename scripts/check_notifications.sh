#!/bin/bash
# Pre-response check for Jules notifications
# Called by the agent before every response

cd /home/kai/.openclaw/workspace/skills/agent-swarm
python3 scripts/notify_agent.py 2&gt;/dev/null
