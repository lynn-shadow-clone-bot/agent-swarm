
import os
import sys
import unittest
import importlib

# Add scripts directory to path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

class TestDBPath(unittest.TestCase):
    def setUp(self):
        # Save original environment variable
        self.original_swarm_db = os.environ.get("SWARM_DB")
        self.custom_db_path = "/tmp/test_swarm.db"

    def tearDown(self):
        # Restore original environment variable
        if self.original_swarm_db:
            os.environ["SWARM_DB"] = self.original_swarm_db
        elif "SWARM_DB" in os.environ:
            del os.environ["SWARM_DB"]

    def test_orchestrator_db_path_env(self):
        """Test that orchestrator respects SWARM_DB environment variable."""
        os.environ["SWARM_DB"] = self.custom_db_path

        # We need to reload the module because it might have been imported already
        import orchestrator
        importlib.reload(orchestrator)

        self.assertEqual(orchestrator.DB_PATH, self.custom_db_path)

    def test_task_router_db_path_env(self):
        """Test that task_router respects SWARM_DB environment variable."""
        os.environ["SWARM_DB"] = self.custom_db_path

        # We need to reload the module because it might have been imported already
        import task_router
        importlib.reload(task_router)

        self.assertEqual(task_router.DB_PATH, self.custom_db_path)

    def test_orchestrator_db_path_default(self):
        """Test that orchestrator uses default path when SWARM_DB is not set."""
        if "SWARM_DB" in os.environ:
            del os.environ["SWARM_DB"]

        import orchestrator
        importlib.reload(orchestrator)

        expected_path = os.path.join(os.path.dirname(orchestrator.__file__), '..', 'swarm.db')
        self.assertEqual(os.path.abspath(orchestrator.DB_PATH), os.path.abspath(expected_path))

    def test_task_router_db_path_default(self):
        """Test that task_router uses default path when SWARM_DB is not set."""
        if "SWARM_DB" in os.environ:
            del os.environ["SWARM_DB"]

        import task_router
        importlib.reload(task_router)

        expected_path = os.path.join(os.path.dirname(task_router.__file__), '..', 'swarm.db')
        self.assertEqual(os.path.abspath(task_router.DB_PATH), os.path.abspath(expected_path))

if __name__ == '__main__':
    unittest.main()
