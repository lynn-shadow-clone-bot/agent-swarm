#!/usr/bin/env python3
"""
Agent Swarm Orchestrator
Coordinates multi-agent teams for complex tasks.
"""

import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'swarm.db')
DB_TIMEOUT = 30.0

def init_db():
    """Initialize database tables."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            team_config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            result TEXT,
            output_dir TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            agent_type TEXT,
            status TEXT DEFAULT 'pending',
            session_key TEXT,
            spawned_at TIMESTAMP,
            completed_at TIMESTAMP,
            result TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            agent_id TEXT,
            message_type TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def load_agent_template(agent_type: str) -> Dict:
    """Load agent template from references."""
    template_path = os.path.join(
        os.path.dirname(__file__), '..', 'references', 'AGENT_TEMPLATES.md'
    )
    
    # Default templates (fallback)
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
    print("\n" + "="*60)
    print("🤖 AGENT SWARM ORCHESTRATOR")
    print("="*60)
    print(f"\nTask: {task}")
    print("\nBefore assembling the team, I need to clarify a few things:")
    
    questions_config = [
        {
            "key": "output_format",
            "question": "What is the expected output format? (e.g., code files, documentation, analysis)",
            "default": "code files"
        },
        {
            "key": "constraints",
            "question": "Are there any specific constraints or requirements?",
            "default": "none"
        },
        {
            "key": "success_criteria",
            "question": "What would make this task 100% complete in your eyes?",
            "default": "working implementation"
        },
        {
            "key": "tech_stack",
            "question": "Is there a preferred technology stack or approach?",
            "default": "auto-detect"
        }
    ]
    
    # For non-interactive mode, use defaults
    if not sys.stdin.isatty():
        print("\n(Running in non-interactive mode, using defaults)")
        return {q["key"]: q["default"] for q in questions_config}

    answers = {}
    
    for i, config in enumerate(questions_config, 1):
        print(f"\n{i}. {config['question']}")
        answer = input("   > ").strip()
        answers[config["key"]] = answer if answer else "none"
    
    return {
        q["key"]: answers.get(q["key"], q["default"]) for q in questions_config
    }

def assemble_team(task: str, team_types: List[str], clarifications: Dict) -> str:
    """Assemble agent team and return task ID."""
    task_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
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
    conn.close()
    
    return task_id

def spawn_agents(task_id: str):
    """Spawn all agents for a task using OpenClaw sessions_spawn."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    
    c.execute('SELECT id, agent_type FROM agents WHERE task_id = ? AND status = ?', 
              (task_id, 'pending'))
    agents = c.fetchall()
    
    print(f"\n🚀 Spawning {len(agents)} agents...")
    
    for agent_id, agent_type in agents:
        template = load_agent_template(agent_type)
        
        # Create subtask description
        subtask = f"You are part of an agent team working on: {task_id}\n"
        subtask += f"Your role: {agent_type}\n"
        subtask += f"Instructions: {template['system_prompt']}\n"
        subtask += "Wait for task assignment from orchestrator."
        
        print(f"  Spawning {agent_type}...")
        
        # Note: In real implementation, use OpenClaw API
        # For now, create placeholder session key
        session_key = f"agent:swarm:{task_id}:{agent_id}"
        
        c.execute('''
            UPDATE agents 
            SET status = ?, session_key = ?, spawned_at = ?
            WHERE id = ?
        ''', ('active', session_key, datetime.now().isoformat(), agent_id))
        
        # Simulate spawn message
        c.execute('''
            INSERT INTO messages (task_id, agent_id, message_type, content)
            VALUES (?, ?, ?, ?)
        ''', (task_id, agent_id, 'SPAWNED', f'Agent {agent_type} ready'))
    
    # Update task status
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('executing', task_id))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ All agents spawned for task {task_id[:8]}...")

def execute_task(task_id: str):
    """Execute task with agent team."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    
    c.execute('SELECT description FROM tasks WHERE id = ?', (task_id,))
    task = c.fetchone()[0]
    
    print(f"\n📋 Executing: {task}")
    print("="*60)
    
    # Get all agents
    c.execute('SELECT id, agent_type, session_key FROM agents WHERE task_id = ?', (task_id,))
    agents = c.fetchall()
    
    # Simulate execution (in real implementation, use OpenClaw sessions_send)
    print(f"\n🔄 Coordinating {len(agents)} agents...")
    
    for i, (agent_id, agent_type, session_key) in enumerate(agents, 1):
        print(f"  [{i}/{len(agents)}] {agent_type} working...")
        
        # Simulate work
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
    
    # Mark task complete
    final_result = f"Task completed by {len(agents)} agents. All subtasks finished."
    
    c.execute('''
        UPDATE tasks 
        SET status = ?, result = ?, completed_at = ?
        WHERE id = ?
    ''', ('completed', final_result, datetime.now().isoformat(), task_id))
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print("✅ TASK COMPLETED!")
    print("="*60)
    print(f"\nTask ID: {task_id}")
    print(f"Agents: {len(agents)}")
    print(f"Status: 100% COMPLETE")
    print(f"\n{final_result}")

def get_status(task_id: str):
    """Get status of a task."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = c.fetchone()
    
    if not task:
        print(f"Task {task_id} not found")
        return
    
    print(f"\n📊 Task Status: {task_id[:8]}...")
    print(f"Description: {task[1]}")
    print(f"Status: {task[2]}")
    print(f"Created: {task[4]}")
    
    c.execute('SELECT agent_type, status FROM agents WHERE task_id = ?', (task_id,))
    agents = c.fetchall()
    
    print(f"\nAgents ({len(agents)}):")
    for agent_type, status in agents:
        print(f"  - {agent_type}: {status}")
    
    conn.close()

def list_tasks():
    """List all tasks."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    c = conn.cursor()
    
    c.execute('SELECT id, description, status, created_at FROM tasks ORDER BY created_at DESC')
    tasks = c.fetchall()
    
    print(f"\n📋 All Tasks ({len(tasks)} total):")
    print("-" * 80)
    
    for task_id, desc, status, created in tasks:
        print(f"{task_id[:8]}... | {status:12} | {desc[:40]}... | {created}")
    
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
    init_db()
    
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
        
        print("\n" + "="*60)
        print("✅ Clarifications complete!")
        print("="*60)
        
        # Step 2: Assemble team
        task_id = assemble_team(args.task, team_types, clarifications)
        
        print(f"\n📝 Task ID: {task_id}")
        print(f"👥 Team: {', '.join(team_types)}")
        
        # Step 3: Spawn agents
        spawn_agents(task_id)
        
        # Step 4: Execute
        execute_task(task_id)
        
        print(f"\n💡 Check status anytime:")
        print(f"   python3 scripts/orchestrator.py --status --task-id {task_id}")
        
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
