import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add scripts directory to path so we can import orchestrator
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from orchestrator import ask_clarifying_questions

class TestOrchestrator(unittest.TestCase):
    @patch('builtins.input', side_effect=['code', 'none', 'works', 'python'])
    @patch('sys.stdin.isatty', return_value=True)
    def test_ask_clarifying_questions(self, mock_isatty, mock_input):
        result = ask_clarifying_questions("Test task")

        self.assertEqual(result['output_format'], 'code')
        self.assertEqual(result['constraints'], 'none')
        self.assertEqual(result['success_criteria'], 'works')
        self.assertEqual(result['tech_stack'], 'python')

    @patch('builtins.input', side_effect=['', '', '', ''])
    @patch('sys.stdin.isatty', return_value=True)
    def test_ask_clarifying_questions_empty(self, mock_isatty, mock_input):
        result = ask_clarifying_questions("Test task")
        # According to code analysis, interactive empty input results in "none"
        self.assertEqual(result['output_format'], 'none')
        self.assertEqual(result['constraints'], 'none')
        self.assertEqual(result['success_criteria'], 'none')
        self.assertEqual(result['tech_stack'], 'none')

    @patch('sys.stdin.isatty', return_value=False)
    def test_ask_clarifying_questions_non_interactive(self, mock_isatty):
        result = ask_clarifying_questions("Test task")
        self.assertEqual(result['output_format'], 'code files')
        self.assertEqual(result['constraints'], 'none')
        self.assertEqual(result['success_criteria'], 'working implementation')
        self.assertEqual(result['tech_stack'], 'auto-detect')

if __name__ == '__main__':
    unittest.main()
