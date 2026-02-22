import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.security import InputValidator, AuditLogger, SecretsManager

class TestSecurity(unittest.TestCase):

    # --- InputValidator ---
    def test_validate_task_description_valid(self):
        desc = InputValidator.validate_task_description("Valid task description")
        self.assertEqual(desc, "Valid task description")

    def test_validate_task_description_too_long(self):
        long_desc = "a" * 1001
        with self.assertRaises(ValueError):
            InputValidator.validate_task_description(long_desc)

    def test_validate_task_description_empty(self):
        with self.assertRaises(ValueError):
            InputValidator.validate_task_description("")

    def test_validate_team_config_valid(self):
        team = InputValidator.validate_team_config(["architect", "code-writer"])
        self.assertEqual(team, ["architect", "code-writer"])

    def test_validate_team_config_invalid_role(self):
        with self.assertRaises(ValueError):
            InputValidator.validate_team_config(["architect", "hacker"])

    def test_sanitize_filename(self):
        name = InputValidator.sanitize_filename("../etc/passwd")
        self.assertEqual(name, "passwd")

    # --- SecretsManager ---
    def test_mask_secret(self):
        self.assertEqual(SecretsManager.mask_secret("12345678"), "12****78")
        self.assertEqual(SecretsManager.mask_secret("123"), "***")
        self.assertEqual(SecretsManager.mask_secret(None), "")

    @patch.dict(os.environ, {"MY_SECRET": "secret_value"})
    def test_get_secret(self):
        self.assertEqual(SecretsManager.get("MY_SECRET"), "secret_value")

    def test_get_secret_default(self):
        self.assertEqual(SecretsManager.get("MISSING_SECRET", "default"), "default")

    # --- AuditLogger ---
    def test_audit_log_event(self):
        # Mock get_connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('scripts.security.get_connection', return_value=mock_conn):
            logger = AuditLogger(log_file="/tmp/test_audit.log")
            logger.log_event("TEST_EVENT", "user", {"foo": "bar"})

            mock_cursor.execute.assert_called()
            args = mock_cursor.execute.call_args[0]
            self.assertIn("INSERT INTO audit_logs", args[0])
            self.assertEqual(args[1][0], "TEST_EVENT") # event_type

if __name__ == '__main__':
    unittest.main()
