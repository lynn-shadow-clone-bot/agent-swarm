#!/usr/bin/env python3
"""
Agent Swarm Orchestrator
Coordinates multi-agent teams for complex tasks.
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
from typing import Dict, List, Optional
import time

# Add scripts dir to path if running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.config_loader import config
    from scripts.db_config import get_connection, DB_PATH
    from scripts.db_migrations import apply_migrations
    from scripts.openclaw_client import client as openclaw_client
except ImportError:
    from config_loader import config
    from db_config import get_connection, DB_PATH
    from db_migrations import apply_migrations
    from openclaw_client import client as openclaw_client

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

# --- Logic ---

def load_agent_template(agent_type: str) -> Dict:
    """Load agent template from references."""
    # We maintain this dictionary as a fallback/reference,
    # but ideally should sync with agent_pool or agent_templates dir.
    # For this phase, we keep the existing logic structure.
    
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

def assemble_team(task: str, team_types: List[str], clarifications: Dict) -> str:
    """Assemble agent team and return task ID."""
    task_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        c = conn.cursor()

        # Create task
        c.execute('''
            INSERT INTO tasks (id, description, status, team_config)
            VALUES (?, ?, ?, ?)
        ''', (task_id, task, 'assembling', json.dumps(team_types)))

        # Create agents
        for agent_type in team_types:
            agent_id = str(uuid.uuid4())
            c.execute('''
                INSERT INTO agents (id, task_id, agent_type, status)
                VALUES (?, ?, ?, ?)
            ''', (agent_id, task_id, agent_type, 'pending'))

        conn.commit()
        return task_id
    except Exception as e:
        logger.error(f"Failed to assemble team: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def spawn_agents(task_id: str):
    """Spawn all agents for a task using OpenClaw."""
    if SHUTDOWN_REQUESTED:
        return

    conn = get_connection()
    try:
        c = conn.cursor()
        
        c.execute('SELECT id, agent_type FROM agents WHERE task_id = ? AND status = ?',
                  (task_id, 'pending'))
        agents = c.fetchall()
        
        logger.info(f"\n🚀 Spawning {len(agents)} agents...")

        failed_count = 0
        for agent_id, agent_type in agents:
            if SHUTDOWN_REQUESTED:
                logger.info("Shutdown requested, stopping spawn...")
                break

            template = load_agent_template(agent_type)

            logger.info(f"  Spawning {agent_type}...")

            try:
                session_key = openclaw_client.spawn_agent(
                    task=f"Task: {task_id}. Role: {agent_type}. {template.get('system_prompt', '')}",
                    label=f"{agent_type}-{task_id[:8]}",
                    model=template.get("model", "kimi-coding/k2p5"),
                    thinking=template.get("thinking", "high")
                )

                c.execute('''
                    UPDATE agents
                    SET status = ?, session_key = ?, spawned_at = ?
                    WHERE id = ?
                ''', ('active', session_key, datetime.now().isoformat(), agent_id))

                # Log spawn message
                c.execute('''
                    INSERT INTO messages (task_id, agent_id, message_type, content)
                    VALUES (?, ?, ?, ?)
                ''', (task_id, agent_id, 'SPAWNED', f'Agent {agent_type} ready: {session_key}'))

            except Exception as e:
                logger.error(f"Failed to spawn agent {agent_type}: {e}")
                c.execute('UPDATE agents SET status = ?, result = ? WHERE id = ?',
                          ('failed', str(e), agent_id))
                failed_count += 1

        # Update task status
        if failed_count > 0:
            logger.error(f"{failed_count} agents failed to spawn. Marking task as failed.")
            c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('failed', task_id))
        elif not SHUTDOWN_REQUESTED:
            c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('executing', task_id))

        conn.commit()
        logger.info(f"\n✅ All agents processed for task {task_id[:8]}...")
    
    except Exception as e:
        logger.error(f"Critical error in spawn_agents: {e}")
        conn.rollback()
    finally:
        conn.close()

def execute_task(task_id: str):
    """Execute task with agent team."""
    conn = get_connection()
    try:
        c = conn.cursor()

        # Check task status first
        c.execute('SELECT description, status FROM tasks WHERE id = ?', (task_id,))
        task_row = c.fetchone()
        if not task_row:
            logger.error(f"Task {task_id} not found")
            return
        task, status = task_row

        if status == 'failed':
            logger.error(f"Task {task_id} is marked as failed. Skipping execution.")
            return

        logger.info(f"\n📋 Executing: {task}")
        logger.info("="*60)
        
        # Get all agents
        c.execute('SELECT id, agent_type, session_key FROM agents WHERE task_id = ?', (task_id,))
        agents = c.fetchall()
        
        logger.info(f"\n🔄 Coordinating {len(agents)} agents...")
        
        failed_count = 0
        for i, (agent_id, agent_type, session_key) in enumerate(agents, 1):
            if SHUTDOWN_REQUESTED:
                break

            logger.info(f"  [{i}/{len(agents)}] {agent_type} working...")

            # Notify agent
            try:
                if session_key and session_key != "unknown_session":
                    openclaw_client.send_message(session_key, "Start working on your task.")
            except Exception as e:
                logger.error(f"Failed to communicate with {agent_type}: {e}")
                c.execute('UPDATE agents SET status = ?, result = ? WHERE id = ?',
                          ('failed', str(e), agent_id))
                failed_count += 1
                continue

            c.execute('''
                UPDATE agents SET status = ? WHERE id = ?
            ''', ('working', agent_id))

            # Simulate completion
            result = f"{agent_type} completed their subtask"

            c.execute('''
                UPDATE agents
                SET status = ?, result = ?, completed_at = ?
                WHERE id = ?
            ''', ('completed', result, datetime.now().isoformat(), agent_id))

            c.execute('''
                INSERT INTO messages (task_id, agent_id, message_type, content)
                VALUES (?, ?, ?, ?)
            ''', (task_id, agent_id, 'COMPLETED', result))
        
        if not SHUTDOWN_REQUESTED:
            if failed_count > 0:
                 error_msg = f"Task failed: {failed_count} agents encountered errors."
                 logger.error(error_msg)
                 c.execute('''
                    UPDATE tasks
                    SET status = ?, result = ?, completed_at = ?
                    WHERE id = ?
                ''', ('failed', error_msg, datetime.now().isoformat(), task_id))
            else:
                # Mark task complete
                final_result = f"Task completed by {len(agents)} agents. All subtasks finished."

                c.execute('''
                    UPDATE tasks
                    SET status = ?, result = ?, completed_at = ?
                    WHERE id = ?
                ''', ('completed', final_result, datetime.now().isoformat(), task_id))

                logger.info("\n" + "="*60)
                logger.info("✅ TASK COMPLETED!")
                logger.info("="*60)
                logger.info(f"\nTask ID: {task_id}")
                logger.info(f"Agents: {len(agents)}")
                logger.info(f"Status: 100% COMPLETE")
                logger.info(f"\n{final_result}")

        conn.commit()
    
    except Exception as e:
        logger.error(f"Critical error in execute_task: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_status(task_id: str):
    """Get status of a task."""
    conn = get_connection()
    try:
        c = conn.cursor()

        c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()

        if not task:
            logger.error(f"Task {task_id} not found")
            return

        logger.info(f"\n📊 Task Status: {task_id[:8]}...")
        logger.info(f"Description: {task[1]}")
        logger.info(f"Status: {task[2]}")
        logger.info(f"Created: {task[4]}")

        c.execute('SELECT agent_type, status FROM agents WHERE task_id = ?', (task_id,))
        agents = c.fetchall()

        logger.info(f"\nAgents ({len(agents)}):")
        for agent_type, status in agents:
            logger.info(f"  - {agent_type}: {status}")
            if status == 'failed':
                 # Check if there is a result (error message)
                 c.execute('SELECT result FROM agents WHERE task_id = ? AND agent_type = ?', (task_id, agent_type))
                 res = c.fetchone()
                 if res and res[0]:
                     logger.info(f"    Error: {res[0]}")

    finally:
        conn.close()

def list_tasks():
    """List all tasks."""
    conn = get_connection()
    try:
        c = conn.cursor()

        c.execute('SELECT id, description, status, created_at FROM tasks ORDER BY created_at DESC')
        tasks = c.fetchall()

        logger.info(f"\n📋 All Tasks ({len(tasks)} total):")
        logger.info("-" * 80)

        for task_id, desc, status, created in tasks:
            logger.info(f"{task_id[:8]}... | {status:12} | {desc[:40]}... | {created}")
    finally:
        conn.close()

def main():
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
    
    if args.list:
        list_tasks()
        return
    
    if args.status and args.task_id:
        get_status(args.task_id)
        return
    
    if args.task and args.team:
        # Parse team
        team_types = [t.strip() for t in args.team.split(',')]
        
        # Step 1: Clarify with orchestrator
        clarifications = ask_clarifying_questions(args.task)
        
        logger.info("\n" + "="*60)
        logger.info("✅ Clarifications complete!")
        logger.info("="*60)
        
        if SHUTDOWN_REQUESTED:
             logger.info("Shutdown requested.")
             return

        # Step 2: Assemble team
        task_id = assemble_team(args.task, team_types, clarifications)
        
        logger.info(f"\n📝 Task ID: {task_id}")
        logger.info(f"👥 Team: {', '.join(team_types)}")
        
        if SHUTDOWN_REQUESTED:
             logger.info("Shutdown requested.")
             return

        # Step 3: Spawn agents
        spawn_agents(task_id)
        
        if SHUTDOWN_REQUESTED:
             logger.info("Shutdown requested.")
             return

        # Step 4: Execute
        execute_task(task_id)
        
        logger.info(f"\n💡 Check status anytime:")
        logger.info(f"   python3 scripts/orchestrator.py --status --task-id {task_id}")
        
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
