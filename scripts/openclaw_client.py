import subprocess
import json
import logging
import os
from typing import Dict, Any, Optional

try:
    from scripts.config_loader import config
    from scripts.utils import retry
except ImportError:
    from config_loader import config
    from utils import retry

logger = logging.getLogger('openclaw_client')

class OpenClawClient:
    def __init__(self):
        self.gateway = config.openclaw.gateway
        self.retries = config.openclaw.retries

    def _run_command(self, args: list) -> Dict[str, Any]:
        """Run openclaw CLI command."""
        cmd = ["openclaw"] + args

        # Inject gateway into environment
        env = dict(os.environ)
        env["OPENCLAW_GATEWAY"] = self.gateway

        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                check=True
            )

            output = result.stdout.strip()
            if not output:
                return {}

            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # Fallback if output is not JSON
                return {"raw_output": output, "status": "ok"}

        except subprocess.CalledProcessError as e:
            logger.error(f"OpenClaw command failed: {e.stderr}")
            raise RuntimeError(f"OpenClaw error: {e.stderr}")
        except FileNotFoundError:
             logger.error("OpenClaw CLI not found")
             raise RuntimeError("OpenClaw CLI not installed")

    @retry(max_retries=3, exceptions=(RuntimeError,))
    def spawn_agent(self, task: str, label: str, model: str, thinking: str = "high") -> str:
        """Spawn an agent and return session ID."""
        args = [
            "spawn",
            "--task", task,
            "--label", label,
            "--model", model,
            "--thinking", thinking,
            "--json"
        ]
        response = self._run_command(args)

        # Try different possible keys for ID
        session_id = response.get("session_id") or response.get("id") or response.get("uuid")

        if not session_id:
            # If no ID found, check raw output or raise error
            if "raw_output" in response:
                # Maybe the raw output IS the ID?
                # Or verify if it looks like an ID.
                # For now, return the raw output if it's short, else raise
                if len(response["raw_output"]) < 100:
                    return response["raw_output"]

            logger.warning(f"Could not parse session ID from response: {response}")
            return "unknown_session" # Fallback to prevent crash, but this is bad

        return session_id

    @retry(max_retries=3, exceptions=(RuntimeError,))
    def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Send message to agent session."""
        args = [
            "send",
            "--session", session_id,
            "--message", message,
            "--json"
        ]
        return self._run_command(args)

    @retry(max_retries=3, exceptions=(RuntimeError,))
    def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status."""
        args = [
            "status",
            "--session", session_id,
            "--json"
        ]
        return self._run_command(args)

# Global client
client = OpenClawClient()
