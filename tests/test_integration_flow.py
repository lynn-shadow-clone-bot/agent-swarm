import unittest
import sys
import os
import asyncio
import tempfile
import sqlite3
from unittest.mock import MagicMock, patch, AsyncMock

# Set up temp DB path before importing project modules
db_fd, db_path = tempfile.mkstemp()
os.close(db_fd)
os.environ["SWARM_DB"] = db_path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.db_migrations import apply_migrations
from scripts.orchestrator import assemble_team, spawn_agents, execute_task
from scripts.db_config import get_connection

class TestIntegrationFlow(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        # Apply migrations
        apply_migrations()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(db_path):
            os.remove(db_path)
        if "SWARM_DB" in os.environ:
            del os.environ["SWARM_DB"]

    def setUp(self):
        conn = get_connection()
        # Delete agents first due to FK constraint
        conn.execute("DELETE FROM agents")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM messages")
        conn.commit()
        conn.close()

    @patch('scripts.orchestrator.openclaw_client')
    async def test_full_task_flow(self, mock_client):
        # Mock OpenClaw behavior
        mock_client.spawn_agent = AsyncMock(return_value="sess-123")
        mock_client.send_message = AsyncMock(return_value={"status": "ok"})

        task_desc = "Create a login page"
        team = ["architect", "code-writer", "tester"]
        clarifications = {}

        # 1. Assemble Team
        task_id = await assemble_team(task_desc, team, clarifications)
        self.assertIsNotNone(task_id)

        # 2. Spawn Agents
        await spawn_agents(task_id)

        # 3. Execute Task
        await execute_task(task_id)

        conn = get_connection()
        # Verify agents completed
        completed_agents = conn.execute("SELECT count(*) FROM agents WHERE task_id = ? AND status = 'completed'", (task_id,)).fetchone()[0]
        self.assertEqual(completed_agents, 3)

        # Verify task completed
        task = conn.execute("SELECT status, result FROM tasks WHERE id = ?", (task_id,)).fetchone()
        self.assertEqual(task[0], "completed")
        self.assertIn("Task completed", task[1])

        conn.close()

if __name__ == '__main__':
    unittest.main()
