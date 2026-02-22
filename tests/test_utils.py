import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import retry

class TestUtils(unittest.TestCase):
    def test_retry_success(self):
        mock_func = MagicMock(return_value="success")
        mock_func.__name__ = "mock_func"
        decorated = retry(max_retries=3)(mock_func)
        result = decorated()
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_failure_then_success(self):
        mock_func = MagicMock(side_effect=[ValueError("fail"), "success"])
        mock_func.__name__ = "mock_func"
        decorated = retry(max_retries=3, exceptions=(ValueError,))(mock_func)
        result = decorated()
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)

    def test_retry_failure_max_retries(self):
        mock_func = MagicMock(side_effect=ValueError("fail"))
        mock_func.__name__ = "mock_func"
        decorated = retry(max_retries=2, exceptions=(ValueError,), delay=0)(mock_func)
        with self.assertRaises(ValueError):
            decorated()
        self.assertEqual(mock_func.call_count, 3) # initial + 2 retries

if __name__ == '__main__':
    unittest.main()
