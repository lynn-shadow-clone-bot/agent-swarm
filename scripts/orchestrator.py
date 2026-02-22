#!/usr/bin/env python3
"""
Agent Swarm Orchestrator
Coordinates multi-agent teams for complex tasks (Async, Scalable).
"""

import argparse
import json
import os
import sys
import uuid
import signal
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, List, Optional, Any
import time
import asyncio
import hashlib
from itertools import groupby

# Add scripts dir to path if running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.config_loader import config
    from scripts.db_config import get_pool
    from scripts.db_migrations import apply_migrations
    from scripts.openclaw_client import client as openclaw_client
    from scripts.observability import metrics, tracing, alerts
    from scripts.security import InputValidator, audit_logger, SecretsManager
    from scripts.rate_limiter import task_submission_limiter
except ImportError:
    from config_loader import config
    from db_config import get_pool
    from db_migrations import apply_migrations
    from openclaw_client import client as openclaw_client
    from observability import metrics, tracing, alerts
    from security import InputValidator, audit_logger, SecretsManager
    from rate_limiter import task_submission_limiter

# --- Logging Setup ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, config.logging.level))
root_logger.handlers = [] # Clear existing handlers

# File Handler (JSON)
if config.logging.file:
    log_dir = os.path.dirname(config.logging.file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = logging.handlers.RotatingFileHandler(
        config.logging.file,
        maxBytes=config.logging.max_bytes,
        backupCount=config.logging.backup_count
    )
    file_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(file_handler)

# Console Handler (Text)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(message)s'))
root_logger.addHandler(console_handler)

logger = logging.getLogger('orchestrator')

# --- Graceful Shutdown ---
SHUTDOWN_REQUESTED = False

def signal_handler(signum, frame):
    global SHUTDOWN_REQUESTED
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    SHUTDOWN_REQUESTED = True

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# --- DB Helpers ---

def _run_sql(sql, params=(), fetch=None, commit=False):
    pool = get_pool()
    conn = pool.get_connection()
    try:
        c = conn.cursor()
        c.execute(sql, params)
        res = None
        if fetch == 'one':
            res = c.fetchone()
        elif fetch == 'all':
            res = c.fetchall()

        if commit:
            conn.commit()
        return res
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        pool.return_connection(conn)

async def db_execute(sql, params=(), commit=False):
    return await asyncio.to_thread(_run_sql, sql, params, commit=commit)

async def db_query_one(sql, params=()):
    return await asyncio.to_thread(_run_sql, sql, params, fetch='one')

async def db_query_all(sql, params=()):
    return await asyncio.to_thread(_run_sql, sql, params, fetch='all')

# --- Caching Helpers ---

def _get_task_hash(agent_type: str, task_description: str) -> str:
    content = f"{agent_type}:{task_description}"
    return hashlib.sha256(content.encode()).hexdigest()

async def check_cache(agent_type: str, task_description: str) -> Optional[str]:
    """Check if result exists in cache."""
    task_hash = _get_task_hash(agent_type, task_description)
    row = await db_query_one('SELECT result FROM task_cache WHERE task_hash = ?', (task_hash,))
    if row:
        logger.info(f"Cache HIT for {agent_type}")
        return row[0]
    return None

async def save_cache(agent_type: str, task_description: str, result: str):
    """Save result to cache."""
    task_hash = _get_task_hash(agent_type, task_description)
    await db_execute('''
        INSERT OR REPLACE INTO task_cache (task_hash, agent_type, result, created_at)
        VALUES (?, ?, ?, ?)
    ''', (task_hash, agent_type, result, datetime.now().isoformat()), commit=True)


# --- Logic ---

def load_agent_template(agent_type: str) -> Dict:
    """Load agent template from references."""
    templates = {
        "code-writer": {
            "agent_id": "code-writer",
            "model": "kimi-coding/k2p5",
            "thinking": "high",
            "system_prompt": "You are a senior software engineer. Write clean, efficient, well-documented code."
        },
        "code-reviewer": {
            "agent_id": "code-reviewer",
            "model": "kimi-coding/k2p5",
            "thinking": "high",
            "system_prompt": "You are a code reviewer. Analyze code for bugs, security issues, and best practices."
        },
        "tester": {
            "agent_id": "tester",
            "model": "kimi-coding/k2p5",
            "thinking": "high",
            "system_prompt": "You are a QA engineer. Write comprehensive tests and validate implementations."
        },
        "researcher": {
            "agent_id": "researcher",
            "model": "kimi-coding/k2p5",
            "thinking": "high",
            "system_prompt": "You are a technical researcher. Search for information and summarize findings."
        },
        "debugger": {
            "agent_id": "debugger",
            "model": "kimi-coding/k2p5",
            "thinking": "high",
            "system_prompt": "You are a debugging expert. Analyze errors and find root causes."
        },
        "architect": {
            "agent_id": "architect",
            "model": "kimi-coding/k2p5",
            "thinking": "high",
            "system_prompt": "You are a software architect. Design scalable, maintainable systems."
        },
        "documenter": {
            "agent_id": "documenter",
            "model": "kimi-coding/k2p5",
            "thinking": "medium",
            "system_prompt": "You are a technical writer. Write clear, concise documentation."
        },
        "optimizer": {
            "agent_id": "optimizer",
            "model": "kimi-coding/k2p5",
            "thinking": "high",
            "system_prompt": "You are a performance engineer. Optimize code for efficiency."
        }
    }
    
    return templates.get(agent_type, templates["code-writer"])

def ask_clarifying_questions(task: str) -> Dict:
    """Ask user clarifying questions before starting."""
    logger.info("="*60)
    logger.info("🤖 AGENT SWARM ORCHESTRATOR")
    logger.info("="*60)
    logger.info(f"\nTask: {task}")
    logger.info("\nBefore assembling the team, I need to clarify a few things:")
    
    questions = [
        "What is the expected output format? (e.g., code files, documentation, analysis)",
        "Are there any specific constraints or requirements?",
        "What would make this task 100% complete in your eyes?",
        "Is there a preferred technology stack or approach?"
    ]
    
    answers = {}
    
    # For non-interactive mode, use defaults
    if not sys.stdin.isatty():
        logger.info("\n(Running in non-interactive mode, using defaults)")
        return {
            "output_format": "code files",
            "constraints": "none",
            "success_criteria": "working implementation",
            "tech_stack": "auto-detect"
        }
    
    for i, question in enumerate(questions, 1):
        print(f"\n{i}. {question}") # Print is fine for prompt
        try:
            answer = input("   > ").strip()
        except EOFError:
            answer = ""
        answers[f"q{i}"] = answer if answer else "none"
    
    return {
        "output_format": answers.get("q1", "code files"),
        "constraints": answers.get("q2", "none"),
        "success_criteria": answers.get("q3", "working implementation"),
        "tech_stack": answers.get("q4", "auto-detect")
    }

async def assemble_team(task: str, team_types: List[str], clarifications: Dict) -> str:
    """Assemble agent team and return task ID."""
    with tracing.get_tracer().start_as_current_span("assemble_team") as span:
        span.set_attribute("task.description", task)
        span.set_attribute("team.size", len(team_types))

        task_id = str(uuid.uuid4())

        try:
            audit_logger.log_event("TEAM_ASSEMBLY_STARTED", "orchestrator", {"task_id": task_id, "team": team_types})

            def _assemble_transaction():
                pool = get_pool()
                conn = pool.get_connection()
                try:
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO tasks (id, description, status, team_config)
                        VALUES (?, ?, ?, ?)
                    ''', (task_id, task, 'assembling', json.dumps(team_types)))

                    for agent_type in team_types:
                        agent_id = str(uuid.uuid4())
                        c.execute('''
                            INSERT INTO agents (id, task_id, agent_type, status, priority)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (agent_id, task_id, agent_type, 'pending', 0))

                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    pool.return_connection(conn)

            await asyncio.to_thread(_assemble_transaction)

            metrics.tasks_created.inc()
            audit_logger.log_event("TASK_CREATED", "orchestrator", {"task_id": task_id})
            return task_id
        except Exception as e:
            logger.error(f"Failed to assemble team: {e}")
            alerts.send_alert("ERROR", f"Failed to assemble team: {e}", {"task": task})
            audit_logger.log_event("TEAM_ASSEMBLY_FAILED", "orchestrator", {"task_id": task_id, "error": str(e)}, status="FAILURE")
            raise

async def spawn_agents(task_id: str):
    """Spawn all agents for a task using OpenClaw."""
    with tracing.get_tracer().start_as_current_span("spawn_agents") as span:
        span.set_attribute("task.id", task_id)
        
        if SHUTDOWN_REQUESTED:
            return

        agents_list = await db_query_all('SELECT id, agent_type FROM agents WHERE task_id = ? AND status = ?', (task_id, 'pending'))

        logger.info(f"\n🚀 Spawning {len(agents_list)} agents...")

        async def _spawn_single(agent_id, agent_type):
            if SHUTDOWN_REQUESTED:
                return False

            template = load_agent_template(agent_type)
            logger.info(f"  Spawning {agent_type}...")

            try:
                with tracing.get_tracer().start_as_current_span("spawn_single_agent") as agent_span:
                    agent_span.set_attribute("agent.type", agent_type)

                    session_key = await openclaw_client.spawn_agent(
                        task=f"Task: {task_id}. Role: {agent_type}. {template.get('system_prompt', '')}",
                        label=f"{agent_type}-{task_id[:8]}",
                        model=template.get("model", "kimi-coding/k2p5"),
                        thinking=template.get("thinking", "high")
                    )

                    await db_execute('''
                        UPDATE agents
                        SET status = ?, session_key = ?, spawned_at = ?
                        WHERE id = ?
                    ''', ('active', session_key, datetime.now().isoformat(), agent_id), commit=True)

                    masked_key = SecretsManager.mask_secret(session_key)
                    await db_execute('''
                        INSERT INTO messages (task_id, agent_id, message_type, content)
                        VALUES (?, ?, ?, ?)
                    ''', (task_id, agent_id, 'SPAWNED', f'Agent {agent_type} ready: {masked_key}'), commit=True)

                    metrics.agents_spawned.labels(agent_type=agent_type).inc()
                    metrics.active_agents.inc()
                    audit_logger.log_event("AGENT_SPAWNED", "orchestrator", {"task_id": task_id, "agent_type": agent_type, "agent_id": agent_id})
                    return True

            except Exception as e:
                logger.error(f"Failed to spawn agent {agent_type}: {e}")
                await db_execute('UPDATE agents SET status = ?, result = ? WHERE id = ?',
                          ('failed', str(e), agent_id), commit=True)
                metrics.agents_failed.labels(agent_type=agent_type).inc()
                alerts.send_alert("ERROR", f"Failed to spawn agent {agent_type}: {e}", {"task_id": task_id})
                audit_logger.log_event("AGENT_SPAWN_FAILED", "orchestrator", {"task_id": task_id, "agent_type": agent_type, "error": str(e)}, status="FAILURE")
                return False

        results = await asyncio.gather(*[_spawn_single(aid, atype) for aid, atype in agents_list])

        failed_count = results.count(False)

        if failed_count > 0:
            logger.error(f"{failed_count} agents failed to spawn. Marking task as failed.")
            await db_execute('UPDATE tasks SET status = ? WHERE id = ?', ('failed', task_id), commit=True)
            audit_logger.log_event("TASK_FAILED_SPAWNING", "orchestrator", {"task_id": task_id, "failed_count": failed_count}, status="FAILURE")
        elif not SHUTDOWN_REQUESTED:
            await db_execute('UPDATE tasks SET status = ? WHERE id = ?', ('executing', task_id), commit=True)

        logger.info(f"\n✅ All agents processed for task {task_id[:8]}...")

async def execute_task(task_id: str):
    """Execute task with agent team (Async, Prioritized, Cached)."""
    with tracing.get_tracer().start_as_current_span("execute_task") as span:
        span.set_attribute("task.id", task_id)
        start_time = time.time()

        task_row = await db_query_one('SELECT description, status, team_config FROM tasks WHERE id = ?', (task_id,))
        if not task_row:
            logger.error(f"Task {task_id} not found")
            return
        task_desc, status, team_config_json = task_row

        if status == 'failed':
            logger.error(f"Task {task_id} is marked as failed. Skipping execution.")
            return

        logger.info(f"\n📋 Executing: {task_desc}")
        logger.info("="*60)

        # 1. Decompose Task using TaskRouter (running in thread to avoid blocking)
        from scripts.task_router import TaskRouter

        def _decompose_and_assign():
            router = TaskRouter()
            try:
                team_types = json.loads(team_config_json)
                subtasks = router.decompose_task(task_desc, team_types)
                router.assign_tasks(task_id, subtasks)
                return subtasks
            finally:
                router.close()

        await asyncio.to_thread(_decompose_and_assign)

        # 2. Execute Subtasks based on Priority
        agents = await db_query_all('''
            SELECT id, agent_type, session_key, result, priority
            FROM agents
            WHERE task_id = ? AND status = 'active'
            ORDER BY priority ASC
        ''', (task_id,))

        logger.info(f"\n🔄 Coordinating {len(agents)} agents (Prioritized)...")

        failed_count = 0

        async def _process_agent(agent_data):
            agent_id, agent_type, session_key, result_json, priority = agent_data

            if SHUTDOWN_REQUESTED: return False

            # Parse subtask
            subtask_desc = "Unknown task"
            if result_json:
                try:
                    subtask_obj = json.loads(result_json)
                    subtask_desc = subtask_obj.get("task", subtask_desc)
                except:
                    pass

            logger.info(f"  [Priority {priority}] {agent_type}: {subtask_desc[:40]}...")

            # CHECK CACHE
            cached_result = await check_cache(agent_type, subtask_desc)
            if cached_result:
                logger.info(f"    -> Using Cached Result for {agent_type}")
                await db_execute('''
                    UPDATE agents
                    SET status = ?, result = ?, completed_at = ?
                    WHERE id = ?
                ''', ('completed', cached_result, datetime.now().isoformat(), agent_id), commit=True)

                await db_execute('''
                    INSERT INTO messages (task_id, agent_id, message_type, content)
                    VALUES (?, ?, ?, ?)
                ''', (task_id, agent_id, 'COMPLETED', cached_result), commit=True)
                return True

            # EXECUTE via OpenClaw
            try:
                if session_key and session_key != "unknown_session":
                    # Send task
                    await openclaw_client.send_message(session_key, f"Execute subtask: {subtask_desc}")

                    await db_execute('UPDATE agents SET status = ? WHERE id = ?', ('working', agent_id), commit=True)

                    # Simulate completion
                    result_msg = f"{agent_type} completed: {subtask_desc}"

                    # SAVE CACHE
                    await save_cache(agent_type, subtask_desc, result_msg)

                    await db_execute('''
                        UPDATE agents
                        SET status = ?, result = ?, completed_at = ?
                        WHERE id = ?
                    ''', ('completed', result_msg, datetime.now().isoformat(), agent_id), commit=True)

                    await db_execute('''
                        INSERT INTO messages (task_id, agent_id, message_type, content)
                        VALUES (?, ?, ?, ?)
                    ''', (task_id, agent_id, 'COMPLETED', result_msg), commit=True)
                    return True
            except Exception as e:
                logger.error(f"Failed to communicate with {agent_type}: {e}")
                await db_execute('UPDATE agents SET status = ?, result = ? WHERE id = ?',
                          ('failed', str(e), agent_id), commit=True)
                return False

        # Group agents by priority and execute groups sequentially
        agents_by_priority = {}
        for a in agents:
            p = a[4] # priority
            if p not in agents_by_priority: agents_by_priority[p] = []
            agents_by_priority[p].append(a)

        sorted_priorities = sorted(agents_by_priority.keys())

        for p in sorted_priorities:
            if SHUTDOWN_REQUESTED: break
            group = agents_by_priority[p]
            logger.info(f"  --- Executing Priority Group {p} ({len(group)} agents) ---")

            group_results = await asyncio.gather(*[_process_agent(a) for a in group])
            failed_count += group_results.count(False)

        if not SHUTDOWN_REQUESTED:
            if failed_count > 0:
                 error_msg = f"Task failed: {failed_count} agents encountered errors."
                 logger.error(error_msg)
                 await db_execute('''
                    UPDATE tasks
                    SET status = ?, result = ?, completed_at = ?
                    WHERE id = ?
                ''', ('failed', error_msg, datetime.now().isoformat(), task_id), commit=True)

                 metrics.tasks_failed.inc()
                 alerts.send_alert("ERROR", error_msg, {"task_id": task_id})
                 audit_logger.log_event("TASK_FAILED", "orchestrator", {"task_id": task_id, "error": error_msg}, status="FAILURE")
            else:
                final_result = f"Task completed by {len(agents)} agents. All subtasks finished."
                await db_execute('''
                    UPDATE tasks
                    SET status = ?, result = ?, completed_at = ?
                    WHERE id = ?
                ''', ('completed', final_result, datetime.now().isoformat(), task_id), commit=True)

                logger.info("\n" + "="*60)
                logger.info("✅ TASK COMPLETED!")
                logger.info("="*60)
                logger.info(f"\nTask ID: {task_id}")
                logger.info(f"Agents: {len(agents)}")
                logger.info(f"Status: 100% COMPLETE")

                metrics.tasks_completed.inc()
                metrics.task_duration.observe(time.time() - start_time)
                audit_logger.log_event("TASK_COMPLETED", "orchestrator", {"task_id": task_id, "duration": time.time() - start_time})

async def get_status(task_id: str):
    """Get status of a task."""
    try:
        task = await db_query_one('SELECT * FROM tasks WHERE id = ?', (task_id,))

        if not task:
            logger.error(f"Task {task_id} not found")
            return

        logger.info(f"\n📊 Task Status: {task_id[:8]}...")
        logger.info(f"Description: {task[1]}")
        logger.info(f"Status: {task[2]}")
        logger.info(f"Created: {task[4]}")

        agents = await db_query_all('SELECT agent_type, status, result FROM agents WHERE task_id = ?', (task_id,))

        logger.info(f"\nAgents ({len(agents)}):")
        for agent_type, status, result in agents:
            logger.info(f"  - {agent_type}: {status}")
            if status == 'failed' and result:
                logger.info(f"    Error: {result}")
            if status == 'completed' and result:
                # result might be JSON or string
                logger.info(f"    Result: {result[:100]}...")

    except Exception as e:
        logger.error(f"Error getting status: {e}")

async def list_tasks():
    """List all tasks."""
    try:
        tasks = await db_query_all('SELECT id, description, status, created_at FROM tasks ORDER BY created_at DESC')

        logger.info(f"\n📋 All Tasks ({len(tasks)} total):")
        logger.info("-" * 80)

        for task_id, desc, status, created in tasks:
            logger.info(f"{task_id[:8]}... | {status:12} | {desc[:40]}... | {created}")
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")

async def async_main():
    parser = argparse.ArgumentParser(description='Agent Swarm Orchestrator')
    parser.add_argument('--task', help='Task description')
    parser.add_argument('--team', help='Comma-separated agent types (e.g., code-writer,tester)')
    parser.add_argument('--status', action='store_true', help='Get task status')
    parser.add_argument('--task-id', help='Task ID for status check')
    parser.add_argument('--list', action='store_true', help='List all tasks')
    parser.add_argument('--output-dir', default='./output', help='Output directory')
    
    args = parser.parse_args()
    
    # Initialize database
    apply_migrations()
    
    # Start metrics server
    metrics.start_server()

    if args.list:
        await list_tasks()
        return
    
    if args.status and args.task_id:
        await get_status(args.task_id)
        return
    
    if args.task and args.team:
        # Rate Limiting
        if not task_submission_limiter.acquire():
             msg = "Rate limit exceeded for task submission. Please try again later."
             logger.error(msg)
             audit_logger.log_event("TASK_SUBMISSION_REJECTED", "cli_user", {"reason": "rate_limit"}, status="FAILURE")
             return

        # Input Validation
        try:
            InputValidator.validate_task_description(args.task)
            team_types = [t.strip() for t in args.team.split(',')]
            InputValidator.validate_team_config(team_types)
        except ValueError as e:
            logger.error(f"Input Validation Error: {e}")
            audit_logger.log_event("TASK_SUBMISSION_REJECTED", "cli_user", {"reason": str(e)}, status="FAILURE")
            return

        audit_logger.log_event("TASK_SUBMISSION_ACCEPTED", "cli_user", {"task": args.task[:50], "team": team_types})

        # Step 1: Clarify (Sync)
        clarifications = ask_clarifying_questions(args.task)
        
        logger.info("\n" + "="*60)
        logger.info("✅ Clarifications complete!")
        logger.info("="*60)
        
        if SHUTDOWN_REQUESTED:
             logger.info("Shutdown requested.")
             return

        # Step 2: Assemble team
        task_id = await assemble_team(args.task, team_types, clarifications)
        
        logger.info(f"\n📝 Task ID: {task_id}")
        logger.info(f"👥 Team: {', '.join(team_types)}")
        
        if SHUTDOWN_REQUESTED:
             logger.info("Shutdown requested.")
             return

        # Step 3: Spawn agents
        await spawn_agents(task_id)
        
        if SHUTDOWN_REQUESTED:
             logger.info("Shutdown requested.")
             return

        # Step 4: Execute
        await execute_task(task_id)
        
        logger.info(f"\n💡 Check status anytime:")
        logger.info(f"   python3 scripts/orchestrator.py --status --task-id {task_id}")
        
    else:
        parser.print_help()

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
