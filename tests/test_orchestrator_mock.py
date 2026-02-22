import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock config before importing orchestrator
with patch('scripts.config_loader.config') as mock_config:
    mock_config.logging.level = 'INFO'
    mock_config.logging.file = None
    mock_config.database.path = ':memory:'
    from scripts.orchestrator import assemble_team, spawn_agents, execute_task, check_cache, save_cache

class TestOrchestratorMock(unittest.IsolatedAsyncioTestCase):

    @patch('scripts.orchestrator.get_pool')
    async def test_assemble_team(self, mock_get_pool):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        task_desc = "Build a website"
        team = ["architect", "code-writer"]
        clarifications = {}

        task_id = await assemble_team(task_desc, team, clarifications)

        self.assertIsInstance(task_id, str)
        # Verify DB inserts
        self.assertEqual(mock_cursor.execute.call_count, 3) # 1 task + 2 agents

    @patch('scripts.orchestrator.db_query_all')
    @patch('scripts.orchestrator.db_execute')
    @patch('scripts.orchestrator.openclaw_client')
    async def test_spawn_agents(self, mock_client, mock_db_execute, mock_db_query_all):
        task_id = "task-1"
        agents_list = [("agent-1", "architect"), ("agent-2", "code-writer")]

        mock_db_query_all.return_value = agents_list
        mock_client.spawn_agent = AsyncMock(return_value="sess-123")

        await spawn_agents(task_id)

        # Verify spawn calls
        self.assertEqual(mock_client.spawn_agent.call_count, 2)
        # Verify status updates
        self.assertTrue(mock_db_execute.called)

    @patch('scripts.orchestrator.db_query_one')
    @patch('scripts.orchestrator.db_query_all')
    @patch('scripts.orchestrator.db_execute')
    @patch('scripts.orchestrator.openclaw_client')
    @patch('scripts.task_router.TaskRouter')
    async def test_execute_task(self, mock_router_cls, mock_client, mock_db_execute, mock_db_query_all, mock_db_query_one):
        task_id = "task-1"

        # Mock task query (first call) and cache check (subsequent calls)
        def query_one_side_effect(sql, params=()):
            if "SELECT description" in sql:
                return ("Build a website", "executing", '["architect", "code-writer"]')
            if "SELECT result FROM task_cache" in sql:
                return None # Cache miss
            return None

        mock_db_query_one.side_effect = query_one_side_effect

        # Mock TaskRouter
        mock_router = MagicMock()
        mock_router.decompose_task.return_value = [
            {"agent_type": "architect", "task": "Design", "priority": 1},
            {"agent_type": "code-writer", "task": "Code", "priority": 2}
        ]
        mock_router_cls.return_value = mock_router

        # Mock active agents query
        # id, agent_type, session_key, result, priority
        mock_db_query_all.return_value = [
            ("agent-1", "architect", "sess-1", '{"task": "Design"}', 1),
            ("agent-2", "code-writer", "sess-2", '{"task": "Code"}', 2)
        ]

        mock_client.send_message = AsyncMock(return_value={"status": "ok"})

        await execute_task(task_id)

        # Verify decomposition
        mock_router.decompose_task.assert_called()
        mock_router.assign_tasks.assert_called()

        # Verify agent execution
        self.assertEqual(mock_client.send_message.call_count, 2)

    @patch('scripts.orchestrator.db_query_one')
    async def test_check_cache_hit(self, mock_db_query_one):
        mock_db_query_one.return_value = ("Cached Result",)

        result = await check_cache("tester", "Test this")
        self.assertEqual(result, "Cached Result")

    @patch('scripts.orchestrator.db_query_one')
    async def test_check_cache_miss(self, mock_db_query_one):
        mock_db_query_one.return_value = None

        result = await check_cache("tester", "Test this")
        self.assertIsNone(result)

    @patch('scripts.orchestrator.db_execute')
    async def test_save_cache(self, mock_db_execute):
        await save_cache("tester", "Test this", "Result")
        mock_db_execute.assert_called_once()

if __name__ == '__main__':
    unittest.main()
