
import unittest
import sqlite3
import tempfile
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts import orchestrator

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for the database
        self.db_fd, self.db_path = tempfile.mkstemp()

        # Patch DB_PATH in orchestrator
        self.patcher = patch('scripts.orchestrator.DB_PATH', self.db_path)
        self.patcher.start()

        # Initialize the database
        orchestrator.init_db()

    def tearDown(self):
        self.patcher.stop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_init_db(self):
        """Test database initialization."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Check if tables exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]

        self.assertIn('tasks', tables)
        self.assertIn('agents', tables)
        self.assertIn('messages', tables)

        conn.close()

    def test_execute_task(self):
        """Test task execution."""
        # Setup: create task and agents
        task_id = orchestrator.assemble_team("Task", ["code-writer"], {})

        # Execute (simulates work)
        with patch('sys.stdout', new_callable=MagicMock):
            orchestrator.spawn_agents(task_id) # Set to active first
            orchestrator.execute_task(task_id)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Verify agents completed
        c.execute("SELECT status, result FROM agents WHERE task_id = ?", (task_id,))
        status, result = c.fetchone()
        self.assertEqual(status, 'completed')
        self.assertIn('completed', result)

        # Verify messages
        c.execute("SELECT content FROM messages WHERE task_id = ? AND message_type = 'COMPLETED'", (task_id,))
        content = c.fetchone()[0]
        self.assertIn('completed', content)

        # Verify task completed
        c.execute("SELECT status, result FROM tasks WHERE id = ?", (task_id,))
        status, result = c.fetchone()
        self.assertEqual(status, 'completed')
        self.assertIn('Task completed', result)

        conn.close()

    def test_get_status(self):
        """Test status retrieval."""
        task_desc = "Status Test Task"
        task_id = orchestrator.assemble_team(task_desc, ["tester"], {})

        # Capture stdout
        mock_stdout = MagicMock()
        with patch('sys.stdout', mock_stdout):
            orchestrator.get_status(task_id)

        # Verify output calls
        # We check if write was called with parts of the expected output
        output = "".join([call.args[0] for call in mock_stdout.write.mock_calls])
        self.assertIn(task_desc, output)
        self.assertIn("assembling", output) # Initial status
        self.assertIn("tester", output)

    def test_load_agent_template(self):
        """Test loading agent templates."""
        # Test loading a known template
        template = orchestrator.load_agent_template('code-writer')
        self.assertEqual(template['agent_id'], 'code-writer')
        self.assertIn('system_prompt', template)

        # Test loading an unknown template (should return default/code-writer)
        template = orchestrator.load_agent_template('unknown-agent')
        self.assertEqual(template['agent_id'], 'code-writer')

    @patch('builtins.input', side_effect=['code', 'none', 'works', 'python'])
    @patch('sys.stdout', new_callable=MagicMock)
    def test_ask_clarifying_questions(self, mock_stdout, mock_input):
        """Test asking clarifying questions."""
        # Force isatty to return True to trigger interactive mode
        with patch('sys.stdin.isatty', return_value=True):
            clarifications = orchestrator.ask_clarifying_questions('Test Task')

            self.assertEqual(clarifications['output_format'], 'code')
            self.assertEqual(clarifications['constraints'], 'none')
            self.assertEqual(clarifications['success_criteria'], 'works')
            self.assertEqual(clarifications['tech_stack'], 'python')

        # Test non-interactive mode
        with patch('sys.stdin.isatty', return_value=False):
            clarifications = orchestrator.ask_clarifying_questions('Test Task')
            self.assertEqual(clarifications['output_format'], 'code files')

    def test_assemble_team(self):
        """Test team assembly."""
        task_desc = "Build a website"
        team_types = ["architect", "code-writer", "tester"]
        clarifications = {
            "output_format": "code",
            "constraints": "none",
            "success_criteria": "working",
            "tech_stack": "python"
        }

        task_id = orchestrator.assemble_team(task_desc, team_types, clarifications)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Verify task created
        c.execute("SELECT description, status, team_config FROM tasks WHERE id = ?", (task_id,))
        task = c.fetchone()
        self.assertIsNotNone(task)
        self.assertEqual(task[0], task_desc)
        self.assertEqual(task[1], 'assembling')
        self.assertEqual(json.loads(task[2]), team_types)

        # Verify agents created
        c.execute("SELECT agent_type, status FROM agents WHERE task_id = ?", (task_id,))
        agents = c.fetchall()
        self.assertEqual(len(agents), 3)
        agent_types = [a[0] for a in agents]
        self.assertCountEqual(agent_types, team_types)
        for _, status in agents:
            self.assertEqual(status, 'pending')

        conn.close()

    def test_spawn_agents(self):
        """Test agent spawning."""
        # Setup: create task and agents
        task_id = orchestrator.assemble_team("Task", ["code-writer"], {})

        # Execute spawn
        with patch('sys.stdout', new_callable=MagicMock):
            orchestrator.spawn_agents(task_id)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Verify agents active
        c.execute("SELECT status, session_key FROM agents WHERE task_id = ?", (task_id,))
        status, key = c.fetchone()
        self.assertEqual(status, 'active')
        self.assertIn(task_id, key)

        # Verify messages
        c.execute("SELECT message_type, content FROM messages WHERE task_id = ?", (task_id,))
        msg_type, content = c.fetchone()
        self.assertEqual(msg_type, 'SPAWNED')
        self.assertIn('ready', content)

        # Verify task executing
        c.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        self.assertEqual(c.fetchone()[0], 'executing')

        conn.close()

if __name__ == '__main__':
    unittest.main()
