import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure scripts dir is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.openclaw_client import OpenClawClient

class TestOpenClawIntegration(unittest.TestCase):

    @patch('subprocess.run')
    def test_spawn_agent(self, mock_run):
        # Setup mock response
        mock_result = MagicMock()
        mock_result.stdout = '{"session_id": "sess-123"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        client = OpenClawClient()
        session_id = client.spawn_agent("Do code", "test-agent", "k2p5")

        self.assertEqual(session_id, "sess-123")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("spawn", args)
        self.assertIn("--task", args)

    @patch('subprocess.run')
    def test_send_message(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"status": "received"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        client = OpenClawClient()
        resp = client.send_message("sess-123", "Hello")

        self.assertEqual(resp["status"], "received")

    @patch('subprocess.run')
    def test_cli_error(self, mock_run):
        mock_run.side_effect = FileNotFoundError("No openclaw")

        client = OpenClawClient()
        with self.assertRaises(RuntimeError):
            client.get_status("sess-123")

if __name__ == '__main__':
    unittest.main()
