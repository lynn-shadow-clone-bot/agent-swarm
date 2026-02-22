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

try:
    from scripts.openclaw_client import client as openclaw_client
except ImportError:
    from openclaw_client import client as openclaw_client

# Configure logging
logger = logging.getLogger('agent_pool')

class AgentPool:
    def __init__(self):
        # Handle path regardless of where script is run from
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agent_templates')

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
        try:
            template = self.load_template(agent_type)
        except Exception as e:
            logger.error(f"Failed to load template for {agent_type}: {e}")
            return None

        task_prompt = f"Task ID: {task_id}. Role: {agent_type}. {template.get('system_prompt', '')}"
        label = f"{agent_type}-{task_id[:8]}"
        model = template.get("model", "kimi-coding/k2p5")
        thinking = template.get("thinking", "high")

        retries = 0
        while retries <= max_retries:
            try:
                logger.info(f"Spawning agent {agent_type} (attempt {retries + 1}/{max_retries + 1})...")
                
                session_id = openclaw_client.spawn_agent(
                    task=task_prompt,
                    label=label,
                    model=model,
                    thinking=thinking
                )
                
                if session_id and session_id != "unknown_session":
                    logger.info(f"Successfully spawned {agent_type}: {session_id}")
                    return session_id
                else:
                    logger.warning(f"Spawned agent {agent_type} but got unknown session ID.")
                
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
    logging.basicConfig(level=logging.INFO)
    pool = AgentPool()
    try:
        # This will fail if openclaw is not installed or templates dir is missing
        pool.spawn_agent("test-task", "code-writer")
    except Exception as e:
        print(f"Test failed: {e}")
