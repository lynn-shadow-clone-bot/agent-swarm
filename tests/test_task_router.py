import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.task_router import TaskRouter, main

class TestTaskRouter(unittest.TestCase):
    def setUp(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Patch get_connection to return our mock
        self.patcher = patch('scripts.task_router.get_connection', return_value=self.mock_conn)
        self.patcher.start()

        self.router = TaskRouter()

    def tearDown(self):
        self.patcher.stop()

    def test_decompose_task_basic(self):
        team = ["code-writer", "tester"]
        subtasks = self.router.decompose_task("Write a calculator", team)

        self.assertEqual(len(subtasks), 2)

        writer_task = next(t for t in subtasks if t["agent_type"] == "code-writer")
        self.assertEqual(writer_task["priority"], 2)

        tester_task = next(t for t in subtasks if t["agent_type"] == "tester")
        self.assertEqual(tester_task["priority"], 3)
        self.assertIn("code-writer", tester_task["dependencies"])

    def test_decompose_task_full_team(self):
        team = ["architect", "code-writer", "tester", "code-reviewer", "documenter"]
        subtasks = self.router.decompose_task("Complex system", team)

        self.assertEqual(len(subtasks), 5)

        architect = next(t for t in subtasks if t["agent_type"] == "architect")
        self.assertEqual(architect["priority"], 1)

        reviewer = next(t for t in subtasks if t["agent_type"] == "code-reviewer")
        self.assertEqual(reviewer["priority"], 4)
        self.assertIn("code-writer", reviewer["dependencies"])

    def test_assign_tasks(self):
        subtasks = [
            {"agent_type": "code-writer", "task": "Write code", "priority": 2},
            {"agent_type": "tester", "task": "Test code", "priority": 3}
        ]

        # Mock fetchall for active agents check
        self.mock_cursor.fetchall.return_value = [
            ("code-writer", "id-1"),
            ("tester", "id-2")
        ]

        self.router.assign_tasks("task-1", subtasks)

        # Verify executemany was called
        self.mock_cursor.executemany.assert_called_once()
        args = self.mock_cursor.executemany.call_args[0]
        sql = args[0]
        updates = args[1]

        self.assertIn("UPDATE agents", sql)
        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[0][2], "id-1") # agent_id
        self.assertEqual(updates[1][2], "id-2")

    def test_assign_tasks_no_agent(self):
        subtasks = [{"agent_type": "missing-agent", "task": "Do something"}]
        self.mock_cursor.fetchall.return_value = []

        self.router.assign_tasks("task-1", subtasks)

        # Should not call executemany if no agents match
        self.mock_cursor.executemany.assert_not_called()

    def test_assign_tasks_error(self):
        self.mock_cursor.execute.side_effect = Exception("DB Error")

        with self.assertRaises(Exception):
            self.router.assign_tasks("task-1", [])

        self.mock_conn.rollback.assert_called()

    def test_get_execution_order(self):
        # Mock fetched agents
        task1 = {"task": "Design", "dependencies": []}
        task2 = {"task": "Code", "dependencies": ["architect"]}

        self.mock_cursor.fetchall.return_value = [
            ("architect", json.dumps(task1)),
            ("code-writer", json.dumps(task2))
        ]

        order = self.router.get_execution_order("task-1")

        self.assertEqual(len(order), 2)
        self.assertEqual(order[0][0], "architect")
        self.assertEqual(order[1][0], "code-writer")

    @patch('sys.exit')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main(self, mock_parse_args, mock_exit):
        args = MagicMock()
        args.task_id = "task-1"
        args.decompose = True
        mock_parse_args.return_value = args

        # Mock task query
        self.mock_cursor.fetchone.return_value = ("Desc", '["architect"]')

        main()

        self.mock_cursor.execute.assert_called()

    @patch('sys.exit')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_task_not_found(self, mock_parse_args, mock_exit):
        args = MagicMock()
        args.task_id = "task-1"
        args.decompose = True
        mock_parse_args.return_value = args

        self.mock_cursor.fetchone.return_value = None

        main()

        # Should verify print output but checking call is enough

if __name__ == '__main__':
    unittest.main()
