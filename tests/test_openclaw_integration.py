import unittest
import sys
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure scripts dir is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.openclaw_client import OpenClawClient

class TestOpenClawIntegration(unittest.IsolatedAsyncioTestCase):

    @patch('asyncio.create_subprocess_exec')
    async def test_spawn_agent(self, mock_exec):
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.stdout.read.return_value = b'{"session_id": "sess-123"}' # Wait, read is not async usually on file, but communicate is
        mock_process.communicate.return_value = (b'{"session_id": "sess-123"}', b'')
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        client = OpenClawClient()
        session_id = await client.spawn_agent("Do code", "test-agent", "k2p5")

        self.assertEqual(session_id, "sess-123")
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        self.assertIn("spawn", args)
        self.assertIn("--task", args)

    @patch('asyncio.create_subprocess_exec')
    async def test_send_message(self, mock_exec):
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b'{"status": "received"}', b'')
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        client = OpenClawClient()
        resp = await client.send_message("sess-123", "Hello")

        self.assertEqual(resp["status"], "received")

    @patch('asyncio.create_subprocess_exec')
    async def test_cli_error(self, mock_exec):
        mock_exec.side_effect = FileNotFoundError("No openclaw")

        client = OpenClawClient()
        with self.assertRaises(RuntimeError):
            await client.get_status("sess-123")

if __name__ == '__main__':
    unittest.main()
