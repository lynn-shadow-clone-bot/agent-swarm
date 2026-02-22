import unittest
import sqlite3
import os
import sys
import shutil
import tempfile
import asyncio
from unittest.mock import MagicMock, patch

# Add scripts dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import orchestrator
from scripts.db_config import get_connection
import scripts.db_config

class TestOrchestratorFailure(unittest.TestCase):
    def setUp(self):
        # Reset connection pool to ensure we use the new DB path
        if scripts.db_config._pool:
            scripts.db_config._pool.close_all()
        scripts.db_config._pool = None

        # Create a temporary directory for the database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test_swarm.db')

        # Patch the database path in db_config
        self.patcher = patch('scripts.db_config.DB_PATH', self.db_path)
        self.patcher.start()

        # Initialize the database
        orchestrator.apply_migrations()

        # Insert a test task
        self.task_id = "test-task-1"
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO tasks (id, description, status, team_config) VALUES (?, ?, ?, ?)",
                  (self.task_id, "Test Task", "assembling", '["code-writer"]'))
        c.execute("INSERT INTO agents (id, task_id, agent_type, status) VALUES (?, ?, ?, ?)",
                  ("agent-1", self.task_id, "code-writer", "pending"))
        conn.commit()
        conn.close()

    def tearDown(self):
        self.patcher.stop()
        if scripts.db_config._pool:
            scripts.db_config._pool.close_all()
        scripts.db_config._pool = None
        shutil.rmtree(self.test_dir)

    @patch('scripts.openclaw_client.client.spawn_agent')
    def test_spawn_failure_handling(self, mock_spawn):
        # Configure mock to raise an exception
        mock_spawn.side_effect = Exception("Simulated Spawn Failure")

        # Run spawn_agents
        asyncio.run(orchestrator.spawn_agents(self.task_id))

        # Check task status
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT status FROM tasks WHERE id = ?", (self.task_id,))
        status = c.fetchone()[0]
        conn.close()

        print(f"Task status after failure: {status}")

        # Now we expect the task to be marked as failed
        self.assertEqual(status, 'failed', "Task status should be 'failed' when spawn fails")

    @patch('scripts.openclaw_client.client.send_message')
    def test_execute_failure_handling(self, mock_send):
        # Setup: Task is executing, agent is active
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = ? WHERE id = ?", ('executing', self.task_id))
        c.execute("UPDATE agents SET status = ?, session_key = ? WHERE id = ?", ('active', 'session-123', 'agent-1'))
        conn.commit()
        conn.close()

        # Configure mock to raise an exception
        mock_send.side_effect = Exception("Simulated Communication Failure")

        # Run execute_task
        asyncio.run(orchestrator.execute_task(self.task_id))

        # Check task status
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT status FROM tasks WHERE id = ?", (self.task_id,))
        status = c.fetchone()[0]
        conn.close()

        print(f"Task status after execution failure: {status}")

        self.assertEqual(status, 'failed', "Task status should be 'failed' when execution fails")

if __name__ == '__main__':
    unittest.main()
