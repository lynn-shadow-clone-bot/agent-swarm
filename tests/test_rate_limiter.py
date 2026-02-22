import unittest
import sys
import os
import time
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.rate_limiter import RateLimiter

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Patch get_connection used inside RateLimiter
        self.patcher = patch('scripts.rate_limiter.get_connection', return_value=self.mock_conn)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_acquire_success(self):
        limiter = RateLimiter("test_limit", 10, 1.0)

        # Mock fetchone -> (tokens, last_updated)
        # 10 tokens, updated now
        self.mock_cursor.fetchone.return_value = (10.0, time.time())

        result = limiter.acquire(1)
        self.assertTrue(result)

        # Check update
        self.mock_conn.execute.assert_called()
        args = self.mock_conn.execute.call_args[0]
        # UPDATE rate_limits SET tokens = ?, last_updated = ? WHERE key = ?
        self.assertAlmostEqual(args[1][0], 9.0) # 10 - 1 = 9

    def test_acquire_fail(self):
        limiter = RateLimiter("test_limit", 10, 1.0)

        # Mock fetchone -> 0 tokens, updated now
        self.mock_cursor.fetchone.return_value = (0.0, time.time())

        result = limiter.acquire(1)
        self.assertFalse(result)

    def test_acquire_refill(self):
        limiter = RateLimiter("test_limit", 10, 1.0) # 1 token per second

        # Mock fetchone -> 0 tokens, updated 5 seconds ago
        self.mock_cursor.fetchone.return_value = (0.0, time.time() - 5)

        result = limiter.acquire(1)
        self.assertTrue(result)

        # Should have refilled 5 tokens, used 1 -> 4
        args = self.mock_conn.execute.call_args[0]
        self.assertAlmostEqual(args[1][0], 4.0, delta=0.1)

    def test_init_new_key(self):
        limiter = RateLimiter("new_key", 10, 1.0)

        # First fetchone returns None (not found)
        self.mock_cursor.fetchone.return_value = None

        limiter.acquire(1)

        # Should insert new row
        self.mock_cursor.execute.assert_any_call(
            'INSERT INTO rate_limits (key, tokens, last_updated) VALUES (?, ?, ?)',
            ('new_key', 10, unittest.mock.ANY)
        )

if __name__ == '__main__':
    unittest.main()
