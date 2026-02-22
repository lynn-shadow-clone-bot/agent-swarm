import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add scripts directory to path to import TaskRouter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from task_router import TaskRouter

class TestTaskRouter(unittest.TestCase):
    @patch('task_router.sqlite3.connect')
    def test_decompose_task_empty_team(self, mock_connect):
        """Test decompose_task with an empty team list."""
        # Setup
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        router = TaskRouter()

        # Action
        subtasks = router.decompose_task("Test task", [])

        # Verify
        self.assertEqual(subtasks, [])

    @patch('task_router.sqlite3.connect')
    def test_decompose_task_valid_team(self, mock_connect):
        """Test decompose_task with a valid team list."""
        # Setup
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        router = TaskRouter()

        # Action
        subtasks = router.decompose_task("Test task", ["architect", "code-writer"])

        # Verify
        self.assertEqual(len(subtasks), 2)
        # Check if architect task is present
        architect_task = next((t for t in subtasks if t['agent_type'] == 'architect'), None)
        self.assertIsNotNone(architect_task)
        # Check if code-writer task is present
        writer_task = next((t for t in subtasks if t['agent_type'] == 'code-writer'), None)
        self.assertIsNotNone(writer_task)

if __name__ == '__main__':
    unittest.main()
