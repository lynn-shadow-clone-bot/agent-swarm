import asyncio
import time
import os
import sys
import tempfile
import random
from unittest.mock import AsyncMock, patch, MagicMock

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
SPAWN_FAILURE_RATE = 0.2
EXEC_FAILURE_RATE = 0.1
DB_FAILURE_RATE = 0.05

async def mock_task_lifecycle_chaos(task_id: int):
    """Simulate a single task lifecycle with chaos."""
    task_desc = f"Chaos Test Task {task_id}"
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

        # Check final status
        conn = get_connection()
        status = conn.execute("SELECT status FROM tasks WHERE id = ?", (tid,)).fetchone()[0]
        conn.close()

        return status, time.time() - start, tid
    except Exception as e:
        # Unexpected crash
        return "crashed", time.time() - start, str(e)

async def run_chaos_test():
    """Run the chaos test."""
    print(f"🔥 Starting Chaos Test: {NUM_TASKS} tasks with concurrency {CONCURRENCY}")
    print(f"   Spawn Failure Rate: {SPAWN_FAILURE_RATE}")
    print(f"   Exec Failure Rate: {EXEC_FAILURE_RATE}")
    print(f"   DB Failure Rate: {DB_FAILURE_RATE}")

    apply_migrations()

    # Mock OpenClaw with chaos
    async def chaos_spawn(*args, **kwargs):
        await asyncio.sleep(random.uniform(0.01, 0.05))
        if random.random() < SPAWN_FAILURE_RATE:
            raise RuntimeError("Chaos: Spawn Failed")
        return f"sess-{random.randint(1000,9999)}"

    async def chaos_send(*args, **kwargs):
        await asyncio.sleep(random.uniform(0.05, 0.2))
        if random.random() < EXEC_FAILURE_RATE:
            raise RuntimeError("Chaos: Exec Failed")
        return {"status": "ok"}

    # Mock DB with chaos (sometimes)
    # We can patch get_connection or db_execute.
    # Patching db_execute in orchestrator is easier for async calls.
    # But synchronous calls use get_connection directly.
    # Let's stick to OpenClaw chaos for now as DB chaos is harder to simulate without breaking migrations/setup.

    with patch('scripts.orchestrator.openclaw_client') as mock_client:
        mock_client.spawn_agent = AsyncMock(side_effect=chaos_spawn)
        mock_client.send_message = AsyncMock(side_effect=chaos_send)

        # Semaphore for concurrency
        sem = asyncio.Semaphore(CONCURRENCY)

        async def bounded_task(i):
            async with sem:
                return await mock_task_lifecycle_chaos(i)

        start_total = time.time()
        results = await asyncio.gather(*[bounded_task(i) for i in range(NUM_TASKS)])
        total_duration = time.time() - start_total

        statuses = [r[0] for r in results]
        completed = statuses.count("completed")
        failed = statuses.count("failed")
        crashed = statuses.count("crashed")

        print("\n📊 Chaos Test Results:")
        print(f"Total Time: {total_duration:.2f}s")
        print(f"Completed: {completed}")
        print(f"Failed (Gracefully): {failed}")
        print(f"Crashed (Unexpected): {crashed}")

        # Verify that failures are roughly expected
        # Spawn failure: 20%. Task has 3 agents. P(all spawn success) = (0.8)^3 = 0.512
        # So ~49% of tasks should fail at spawn.
        # Exec failure: 10%. Task has 3 agents. P(all exec success) = (0.9)^3 = 0.729
        # Total success rate approx 0.512 * 0.729 = 0.37
        # So we expect roughly 37% completion, 63% failure.

        print(f"Completion Rate: {completed/NUM_TASKS*100:.1f}% (Expected ~37%)")

        if crashed > 0:
            print("❌ Some tasks crashed unexpectedly!")
            for r in results:
                if r[0] == "crashed":
                    print(f"  - {r[2]}")
        else:
            print("✅ System handled all failures gracefully.")

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    import logging
    # logging.getLogger("orchestrator").setLevel(logging.WARNING) # Keep logs to see errors
    logging.getLogger("orchestrator").setLevel(logging.ERROR) # Only errors

    asyncio.run(run_chaos_test())
