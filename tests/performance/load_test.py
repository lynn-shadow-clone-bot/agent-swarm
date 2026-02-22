import asyncio
import time
import os
import sys
import tempfile
import random
from unittest.mock import AsyncMock, patch

# Add root directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

# Setup temp DB
db_fd, db_path = tempfile.mkstemp()
os.close(db_fd)
os.environ["SWARM_DB"] = db_path

# Import after setting env
from scripts.db_migrations import apply_migrations
from scripts.orchestrator import assemble_team, spawn_agents, execute_task
from scripts.db_config import get_connection

# Constants
NUM_TASKS = 50
CONCURRENCY = 10

async def mock_task_lifecycle(task_id: int):
    """Simulate a single task lifecycle."""
    task_desc = f"Load Test Task {task_id}"
    team = ["architect", "code-writer", "tester"]
    clarifications = {}

    start = time.time()

    try:
        # 1. Assemble
        tid = await assemble_team(task_desc, team, clarifications)

        # 2. Spawn
        await spawn_agents(tid)

        # 3. Execute
        await execute_task(tid)

        duration = time.time() - start
        return True, duration, tid
    except Exception as e:
        print(f"Task {task_id} failed: {e}")
        return False, time.time() - start, None

async def run_load_test():
    """Run the load test."""
    print(f"🚀 Starting Load Test: {NUM_TASKS} tasks with concurrency {CONCURRENCY}")

    apply_migrations()

    # Mock OpenClaw
    with patch('scripts.orchestrator.openclaw_client') as mock_client:
        # Simulate network delay
        async def delayed_spawn(*args, **kwargs):
            await asyncio.sleep(random.uniform(0.01, 0.05))
            return f"sess-{random.randint(1000,9999)}"

        async def delayed_send(*args, **kwargs):
            await asyncio.sleep(random.uniform(0.05, 0.2))
            return {"status": "ok"}

        mock_client.spawn_agent = AsyncMock(side_effect=delayed_spawn)
        mock_client.send_message = AsyncMock(side_effect=delayed_send)

        # Semaphore for concurrency
        sem = asyncio.Semaphore(CONCURRENCY)

        async def bounded_task(i):
            async with sem:
                return await mock_task_lifecycle(i)

        start_total = time.time()
        results = await asyncio.gather(*[bounded_task(i) for i in range(NUM_TASKS)])
        total_duration = time.time() - start_total

        successes = [r for r in results if r[0]]
        failures = [r for r in results if not r[0]]

        print("\n📊 Load Test Results:")
        print(f"Total Time: {total_duration:.2f}s")
        print(f"Throughput: {NUM_TASKS / total_duration:.2f} tasks/sec")
        print(f"Success Rate: {len(successes)}/{NUM_TASKS} ({len(successes)/NUM_TASKS*100:.1f}%)")

        if successes:
            avg_latency = sum(r[1] for r in successes) / len(successes)
            print(f"Avg Task Latency: {avg_latency:.2f}s")

        if failures:
            print(f"Failures: {len(failures)}")

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    # Disable logging for load test to reduce noise
    import logging
    logging.getLogger("orchestrator").setLevel(logging.WARNING)
    logging.getLogger("task_router").setLevel(logging.WARNING)

    asyncio.run(run_load_test())
