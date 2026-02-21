#!/usr/bin/env python3
"""
Agent Pool
Manages spawning and lifecycle of agents with retry logic.
"""

import json
import os
import time
import logging
from typing import Dict, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('agent_pool')

# Try to import openclaw
try:
    from openclaw import sessions_spawn, sessions_send, subagents
except ImportError:
    # For environments where openclaw is not installed, we can't run agent logic.
    # We define placeholders to allow the script to be imported/checked, but runtime will fail.
    logger.warning("openclaw module not found. Agent spawning will fail.")
    def sessions_spawn(*args, **kwargs): raise NotImplementedError("openclaw not installed")
    def sessions_send(*args, **kwargs): raise NotImplementedError("openclaw not installed")
    def subagents(*args, **kwargs): raise NotImplementedError("openclaw not installed")

class AgentPool:
    def __init__(self):
        self.templates_dir = os.path.join(os.path.dirname(__file__), '..', 'agent_templates')

    def load_template(self, agent_type: str) -> Dict:
        """Load agent template from JSON file."""
        template_path = os.path.join(self.templates_dir, f"{agent_type}.json")
        if not os.path.exists(template_path):
            # Try to map 'reviewer' to 'code-reviewer' if exact match fails
            if agent_type == 'reviewer':
                return self.load_template('code-reviewer')

            logger.error(f"Template not found: {template_path}")
            raise ValueError(f"Unknown agent type: {agent_type}")

        with open(template_path, 'r') as f:
            return json.load(f)

    def spawn_agent(self, task_id: str, agent_type: str, max_retries: int = 3) -> Optional[str]:
        """Spawn an agent with retry logic."""
        template = self.load_template(agent_type)

        # Prepare spawn arguments
        spawn_args = {
            "task": f"Task ID: {task_id}. Role: {agent_type}. {template['system_prompt']}",
            "label": f"{agent_type}-{task_id[:8]}",
            "model": template.get("model", "kimi-coding/k2p5"),
            "thinking": template.get("thinking", "high")
        }

        retries = 0
        while retries <= max_retries:
            try:
                logger.info(f"Spawning agent {agent_type} (attempt {retries + 1}/{max_retries + 1})...")
                session = sessions_spawn(**spawn_args)

                # Check if session creation was successful
                # The return value of sessions_spawn depends on the API.
                # Assuming it returns a session object or ID.
                # If it's a dict and has an error key, or if it raises exception.

                if session:
                    logger.info(f"Successfully spawned {agent_type}: {session}")
                    return session

            except Exception as e:
                logger.error(f"Failed to spawn agent {agent_type}: {e}")

            retries += 1
            if retries <= max_retries:
                wait_time = 2 ** retries # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        logger.error(f"Failed to spawn agent {agent_type} after {max_retries + 1} attempts.")
        return None

if __name__ == "__main__":
    # Test the pool
    pool = AgentPool()
    try:
        # This will likely fail without openclaw or mock
        pool.spawn_agent("test-task", "code-writer")
    except Exception as e:
        print(f"Test failed: {e}")
