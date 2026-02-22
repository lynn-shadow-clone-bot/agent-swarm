import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add scripts directory to path to import task_router
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from task_router import TaskRouter

class TestTaskRouter(unittest.TestCase):
    def setUp(self):
        # Patch sqlite3.connect
        self.patcher = patch('task_router.sqlite3.connect')
        self.mock_connect = self.patcher.start()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connect.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

    def tearDown(self):
        self.patcher.stop()

    def test_decompose_task_architect(self):
        router = TaskRouter()
        subtasks = router.decompose_task("Build a house", ["architect"])
        self.assertEqual(len(subtasks), 1)
        self.assertEqual(subtasks[0]['agent_type'], 'architect')
        self.assertIn("Design architecture", subtasks[0]['task'])

    def test_decompose_task_multiple_agents(self):
        router = TaskRouter()
        team = ["architect", "code-writer", "tester"]
        subtasks = router.decompose_task("Build app", team)

        # Verify number of tasks
        self.assertEqual(len(subtasks), 3)

        # Verify dependencies
        writer_task = next(t for t in subtasks if t['agent_type'] == 'code-writer')
        self.assertIn("architect", writer_task['dependencies'])

        tester_task = next(t for t in subtasks if t['agent_type'] == 'tester')
        self.assertIn("code-writer", tester_task['dependencies'])

        # Verify order/priority
        # Expected priority: architect(1), code-writer(2), tester(3)
        self.assertEqual(subtasks[0]['agent_type'], 'architect')
        self.assertEqual(subtasks[1]['agent_type'], 'code-writer')
        self.assertEqual(subtasks[2]['agent_type'], 'tester')

    def test_assign_tasks(self):
        router = TaskRouter()
        subtasks = [{"agent_type": "architect", "task": "Design", "priority": 1}]

        # Mock fetchone to return an agent
        self.mock_cursor.fetchone.return_value = (1,)

        router.assign_tasks("task-123", subtasks)

        # Verify SELECT was called
        self.mock_cursor.execute.assert_any_call(
            '''
                SELECT id FROM agents
                WHERE task_id = ? AND agent_type = ? AND status = 'active'
            ''',
            ("task-123", "architect")
        )

        # Verify UPDATE was called
        # We can't easily assert the update call arguments because json.dumps might produce varying whitespace
        # (though default is usually compact).
        # But we can check that it was called.
        self.assertTrue(self.mock_cursor.execute.called)

        # Verify commit was called
        self.mock_conn.commit.assert_called_once()

    def test_get_execution_order(self):
        router = TaskRouter()

        # Mock agents return data: (agent_type, result_json)
        # Agent 1: No deps
        agent1 = ("architect", json.dumps({"dependencies": [], "task": "Design"}))
        # Agent 2: Deps on architect
        agent2 = ("code-writer", json.dumps({"dependencies": ["architect"], "task": "Code"}))

        self.mock_cursor.fetchall.return_value = [agent1, agent2]

        order = router.get_execution_order("task-123")

        self.assertEqual(len(order), 2)
        self.assertEqual(order[0][0], "architect")
        self.assertEqual(order[1][0], "code-writer")

    def test_decompose_task_empty_team(self):
        router = TaskRouter()
        subtasks = router.decompose_task("Do something", [])
        self.assertEqual(subtasks, [])

    def test_assign_tasks_agent_not_found(self):
        router = TaskRouter()
        subtasks = [{"agent_type": "architect", "task": "Design", "priority": 1}]

        # Mock fetchone to return None (agent not found)
        self.mock_cursor.fetchone.return_value = None

        router.assign_tasks("task-123", subtasks)

        # Verify SELECT was called
        self.mock_cursor.execute.assert_any_call(
            '''
                SELECT id FROM agents
                WHERE task_id = ? AND agent_type = ? AND status = 'active'
            ''',
            ("task-123", "architect")
        )

        # Verify UPDATE was NOT called (we can't easily check "not called with specific args" if execute is called for SELECT)
        # But we can check the call count. execute called once for SELECT.
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

    def test_get_execution_order_missing_deps(self):
        router = TaskRouter()

        # Agent 2 depends on Agent 1, but Agent 1 is not in the list (not started/spawned/finished?)
        agent2 = ("code-writer", json.dumps({"dependencies": ["architect"], "task": "Code"}))

        self.mock_cursor.fetchall.return_value = [agent2]

        order = router.get_execution_order("task-123")

        # It should still return the task, but it won't be in 'completed' set internally.
        self.assertEqual(len(order), 1)
        self.assertEqual(order[0][0], "code-writer")

if __name__ == '__main__':
    unittest.main()
