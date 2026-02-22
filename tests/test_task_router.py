import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add scripts directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from task_router import TaskRouter

class TestTaskRouter(unittest.TestCase):

    @patch('sqlite3.connect')
    def setUp(self, mock_connect):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        mock_connect.return_value = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

        self.router = TaskRouter()

    def test_decompose_task_architect(self):
        task_desc = "Build a web app"
        team = ["architect"]

        subtasks = self.router.decompose_task(task_desc, team)

        self.assertEqual(len(subtasks), 1)
        self.assertEqual(subtasks[0]['agent_type'], "architect")
        self.assertEqual(subtasks[0]['priority'], 1)
        self.assertEqual(subtasks[0]['dependencies'], [])

    def test_decompose_task_code_writer_dependencies(self):
        task_desc = "Build a web app"
        team = ["architect", "code-writer"]

        subtasks = self.router.decompose_task(task_desc, team)

        architect_task = next(t for t in subtasks if t['agent_type'] == "architect")
        writer_task = next(t for t in subtasks if t['agent_type'] == "code-writer")

        self.assertEqual(writer_task['dependencies'], ["architect"])
        self.assertTrue(architect_task['priority'] < writer_task['priority'])

    def test_decompose_task_tester_dependencies(self):
        task_desc = "Build a web app"
        team = ["code-writer", "tester"]

        subtasks = self.router.decompose_task(task_desc, team)

        writer_task = next(t for t in subtasks if t['agent_type'] == "code-writer")
        tester_task = next(t for t in subtasks if t['agent_type'] == "tester")

        self.assertEqual(tester_task['dependencies'], ["code-writer"])
        self.assertTrue(writer_task['priority'] < tester_task['priority'])

    def test_decompose_task_sorting(self):
        task_desc = "Build a web app"
        team = ["tester", "architect", "code-writer"]

        subtasks = self.router.decompose_task(task_desc, team)

        priorities = [t['priority'] for t in subtasks]
        self.assertEqual(priorities, sorted(priorities))

        # Verify order: architect (1) -> code-writer (2) -> tester (3)
        self.assertEqual(subtasks[0]['agent_type'], "architect")
        self.assertEqual(subtasks[1]['agent_type'], "code-writer")
        self.assertEqual(subtasks[2]['agent_type'], "tester")

    def test_decompose_task_empty_team(self):
        subtasks = self.router.decompose_task("Task", [])
        self.assertEqual(subtasks, [])

    def test_decompose_task_all_roles(self):
        team = [
            "architect", "code-writer", "tester", "code-reviewer",
            "researcher", "debugger", "documenter", "optimizer"
        ]
        task_desc = "Complex task"

        subtasks = self.router.decompose_task(task_desc, team)

        self.assertEqual(len(subtasks), 8)

        # Verify specific dependencies
        reviewer = next(t for t in subtasks if t['agent_type'] == "code-reviewer")
        self.assertEqual(reviewer['dependencies'], ["code-writer"])

        documenter = next(t for t in subtasks if t['agent_type'] == "documenter")
        self.assertEqual(documenter['dependencies'], ["code-writer"])

        optimizer = next(t for t in subtasks if t['agent_type'] == "optimizer")
        self.assertEqual(optimizer['dependencies'], ["code-writer"])

    def tearDown(self):
        self.router.close()

if __name__ == '__main__':
    unittest.main()
