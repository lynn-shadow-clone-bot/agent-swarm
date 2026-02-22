import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import sqlite3

# Ensure scripts can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to test
# Note: These imports might trigger code if not careful, but we are importing modules
from scripts import task_router
from scripts import orchestrator
from scripts.db_config import DB_TIMEOUT, DB_PATH

class TestDBTimeout(unittest.TestCase):

    @patch('sqlite3.connect')
    def test_task_router_timeout(self, mock_connect):
        """Verify TaskRouter connects with the correct timeout."""
        # Setup mock
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Instantiate TaskRouter
        router = task_router.TaskRouter()

        # Verify sqlite3.connect was called with expected arguments
        # DB_PATH is imported into task_router, so we can check against it
        # or check against the global DB_PATH
        mock_connect.assert_called_with(database=DB_PATH, timeout=DB_TIMEOUT)

        # Cleanup
        router.close()

    @patch('sqlite3.connect')
    def test_orchestrator_init_db_timeout(self, mock_connect):
        """Verify orchestrator.init_db connects with the correct timeout."""
        # Setup mock
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # Call init_db
        orchestrator.init_db()

        # Verify
        mock_connect.assert_called_with(DB_PATH, timeout=DB_TIMEOUT)

    @patch('sqlite3.connect')
    def test_orchestrator_assemble_team_timeout(self, mock_connect):
        """Verify orchestrator.assemble_team connects with the correct timeout."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        # We need to pass valid arguments to assemble_team
        # It takes: task: str, team_types: List[str], clarifications: Dict
        orchestrator.assemble_team("test task", ["code-writer"], {})

        mock_connect.assert_called_with(DB_PATH, timeout=DB_TIMEOUT)

if __name__ == '__main__':
    unittest.main()
