import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock config
with patch('scripts.config_loader.config') as mock_config:
    mock_config.logging.level = 'INFO'
    mock_config.logging.file = None
    mock_config.database.path = ':memory:'
    from scripts.orchestrator import get_status, list_tasks

class TestOrchestratorCLI(unittest.IsolatedAsyncioTestCase):

    @patch('scripts.orchestrator.db_query_one')
    @patch('scripts.orchestrator.db_query_all')
    async def test_get_status_success(self, mock_query_all, mock_query_one):
        mock_query_one.return_value = ("id-1", "Build website", "executing", "none", "2024-01-01")
        mock_query_all.return_value = [("architect", "active", "")]

        await get_status("id-1")

        # Verify calls
        mock_query_one.assert_called()
        mock_query_all.assert_called()

    @patch('scripts.orchestrator.db_query_one')
    async def test_get_status_not_found(self, mock_query_one):
        mock_query_one.return_value = None

        await get_status("missing-id")

        # Should verify logger error, but just ensuring no crash
        mock_query_one.assert_called()

    @patch('scripts.orchestrator.db_query_all')
    async def test_list_tasks(self, mock_query_all):
        mock_query_all.return_value = [
            ("id-1", "Task 1", "completed", "2024-01-01"),
            ("id-2", "Task 2", "failed", "2024-01-02")
        ]

        await list_tasks()

        mock_query_all.assert_called()

if __name__ == '__main__':
    unittest.main()
