#!/usr/bin/env python3
"""
Agent Swarm Orchestrator
Coordinates multi-agent teams for complex tasks using OpenClaw.
"""

import argparse
import json
import os
import sqlite3
import sys
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('orchestrator')

# Add scripts directory to path to allow imports
sys.path.append(os.path.dirname(__file__))

try:
    from agent_pool import AgentPool
except ImportError:
    # If running from root
    from scripts.agent_pool import AgentPool

# OpenClaw imports
try:
    from openclaw import sessions_spawn, sessions_send, subagents
except ImportError:
    logger.warning("openclaw module not found. Agent logic will fail.")
    def sessions_spawn(*args, **kwargs): raise NotImplementedError("openclaw not installed")
    def sessions_send(*args, **kwargs): raise NotImplementedError("openclaw not installed")
    def subagents(*args, **kwargs): raise NotImplementedError("openclaw not installed")

# Database setup
DB_PATH = os.environ.get('SWARM_DB_PATH', '/home/kai/.openclaw/workspace/skills/agent-swarm/swarm.db')

def init_db():
    """Initialize database tables."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
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

def ask_clarifying_questions(task: str) -> Dict:
    """Ask user clarifying questions before starting."""
    print("\n" + "="*60)
    print("🤖 AGENT SWARM ORCHESTRATOR")
    print("="*60)
    print(f"\nTask: {task}")
    print("\nBefore assembling the team, I need to clarify a few things:")
    
    questions = [
        "What is the expected output format? (e.g., code files, documentation, analysis)",
        "Are there any specific constraints or requirements?",
        "What would make this task 100% complete in your eyes?",
        "Is there a preferred technology stack or approach?"
    ]
    
    answers = {}
    
    # For non-interactive mode, use defaults
    if not sys.stdin.isatty():
        print("\n(Running in non-interactive mode, using defaults)")
        return {
            "output_format": "code files",
            "constraints": "none",
            "success_criteria": "working implementation",
            "tech_stack": "auto-detect"
        }
    
    for i, question in enumerate(questions, 1):
        print(f"\n{i}. {question}")
        answer = input("   > ").strip()
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
    
    conn = sqlite3.connect(DB_PATH)
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
    """Spawn all agents for a task using AgentPool."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT id, agent_type FROM agents WHERE task_id = ? AND status = ?', 
              (task_id, 'pending'))
    agents = c.fetchall()
    
    if not agents:
        logger.info("No pending agents to spawn.")
        conn.close()
        return

    print(f"\n🚀 Spawning {len(agents)} agents...")
    pool = AgentPool()
    
    for agent_id, agent_type in agents:
        print(f"  Spawning {agent_type}...")
        
        session = pool.spawn_agent(task_id, agent_type)
        
        if session:
            # Handle session object (dict or string)
            if isinstance(session, dict):
                session_key = str(session.get('id', session))
            else:
                session_key = str(session)
            
            c.execute('''
                UPDATE agents 
                SET status = ?, session_key = ?, spawned_at = ?
                WHERE id = ?
            ''', ('active', session_key, datetime.now().isoformat(), agent_id))
            
            c.execute('''
                INSERT INTO messages (task_id, agent_id, message_type, content)
                VALUES (?, ?, ?, ?)
            ''', (task_id, agent_id, 'SPAWNED', f'Agent {agent_type} ready with session {session_key}'))
        else:
            logger.error(f"Failed to spawn agent {agent_type}")
            c.execute('''
                UPDATE agents SET status = ? WHERE id = ?
            ''', ('failed', agent_id))

    
    # Update task status
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('executing', task_id))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Agents spawned for task {task_id[:8]}...")

def get_agent_output(session_key):
    """Retrieve output from an agent session using subagents list."""
    # In a real implementation, we might need to poll subagents(action='list') 
    # and look for the specific session's output or status.
    try:
        agents_list = subagents(action='list')
        # Assuming agents_list is a list of dicts.
        # Structure might be [{'id': '...', 'status': '...', 'output': '...'}, ...]
        # or similar.
        for agent in agents_list:
            # Match by session key or ID
            if str(agent.get('id')) == str(session_key) or str(agent.get('session_id')) == str(session_key):
                return agent
    except Exception as e:
        logger.error(f"Error checking subagents: {e}")
    return None

def execute_task(task_id: str):
    """Execute task with agent team implementing consensus workflow."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT description FROM tasks WHERE id = ?', (task_id,))
    task_desc = c.fetchone()[0]
    
    print(f"\n📋 Executing: {task_desc}")
    print("="*60)
    
    # Get all active agents
    c.execute('SELECT id, agent_type, session_key FROM agents WHERE task_id = ? AND status = ?', (task_id, 'active'))
    agents = c.fetchall()
    
    # Map agent types to their details
    agent_map = {atype: {'id': aid, 'key': key} for aid, atype, key in agents}
    
    # Workflow: code-writer -> tester -> reviewer
    # This is a simplified sequential workflow managed by the orchestrator.
    
    workflow = ['code-writer', 'tester', 'reviewer', 'code-reviewer']
    
    # Check which agents are present in the team
    active_workflow = [role for role in workflow if role in agent_map]
    
    if not active_workflow:
        print("No workflow agents found. Running generic monitoring.")
        # Just monitor all agents
        monitor_agents(task_id, agents)
        return

    print(f"\n🔄 Starting workflow: {' -> '.join(active_workflow)}")
    
    previous_output = ""
    workflow_idx = 0
    max_rejections = 3
    rejection_count = 0
    
    while workflow_idx < len(active_workflow):
        role = active_workflow[workflow_idx]
        agent_info = agent_map[role]
        print(f"\n👉 Activating {role}...")
        
        # Send instruction to agent to start their part
        start_message = f"START YOUR TASK. "
        if previous_output:
            start_message += f"\n\nCONTEXT FROM PREVIOUS AGENT:\n{previous_output}"
            
        try:
            sessions_send(agent_info['key'], start_message)
        except Exception as e:
            logger.error(f"Failed to send start message to {role}: {e}")
        
        completed = False
        while not completed:
            time.sleep(5) # Poll interval
            
            agent_data = get_agent_output(agent_info['key'])
            if agent_data:
                status = agent_data.get('status', 'unknown')
                print(f"   {role}: {status}", end='\r')
                
                if status in ['completed', 'done']:
                    print(f"\n   ✅ {role} finished.")
                    
                    # Store result
                    result = agent_data.get('output', 'No output')
                    previous_output = result # Save for next agent
                    
                    c.execute('''
                        UPDATE agents 
                        SET status = ?, result = ?, completed_at = ?
                        WHERE id = ?
                    ''', ('completed', result, datetime.now().isoformat(), agent_info['id']))
                    conn.commit()
                    
                    # Reviewer check
                    if role in ['code-reviewer', 'reviewer']:
                        if "REJECT" in result or "reject" in result:
                            rejection_count += 1
                            if rejection_count <= max_rejections:
                                print(f"\n❌ Reviewer rejected ({rejection_count}/{max_rejections}). Looping back...")
                                # Find code-writer index to restart loop
                                try:
                                    cw_idx = active_workflow.index('code-writer')
                                    workflow_idx = cw_idx - 1 # Will increment at end of loop
                                    
                                    # Update context with rejection feedback
                                    previous_output = f"REVIEWER REJECTED. FEEDBACK:\n{result}\n\nPLEASE FIX AND RESUBMIT."
                                    
                                    # Reset statuses for affected agents
                                    for reset_role in active_workflow[cw_idx:]:
                                        if reset_role in agent_map:
                                            c.execute("UPDATE agents SET status = 'active' WHERE id = ?", 
                                                      (agent_map[reset_role]['id'],))
                                    conn.commit()
                                except ValueError:
                                    logger.warning("code-writer not found, cannot loop back.")
                            else:
                                print("\n❌ Max rejections reached. Proceeding...")
                    
                    completed = True
                elif status == 'failed':
                    print(f"\n   ❌ {role} failed.")
                    c.execute("UPDATE agents SET status = 'failed' WHERE id = ?", (agent_info['id'],))
                    conn.commit()
                    completed = True
        
        workflow_idx += 1
                    
    
    # Mark task complete
    final_result = "Workflow completed."
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

def monitor_agents(task_id, agents):
    """Generic monitoring for non-workflow teams."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    pending = len(agents)
    print(f"Monitoring {pending} agents...")
    
    while pending > 0:
        time.sleep(5)
        for agent_id, agent_type, session_key in agents:
            # Check status
            agent_data = get_agent_output(session_key)
            if agent_data:
                status = agent_data.get('status')
                if status in ['completed', 'done', 'failed']:
                    # Check if we already marked it
                    c.execute("SELECT status FROM agents WHERE id = ?", (agent_id,))
                    current_status = c.fetchone()[0]
                    if current_status == 'active':
                        c.execute('''
                            UPDATE agents 
                            SET status = ?, completed_at = ?
                            WHERE id = ?
                        ''', (status, datetime.now().isoformat(), agent_id))
                        conn.commit()
                        pending -= 1
                        print(f"Agent {agent_type} finished with status: {status}")
    
    conn.close()

def get_status(task_id: str):
    """Get status of a task."""
    conn = sqlite3.connect(DB_PATH)
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
    
    c.execute('SELECT agent_type, status, result FROM agents WHERE task_id = ?', (task_id,))
    agents = c.fetchall()
    
    print(f"\nAgents ({len(agents)}):")
    for agent_type, status, result in agents:
        print(f"  - {agent_type}: {status}")
        if result:
            print(f"    Result: {result[:100]}...")
    
    conn.close()

def list_tasks():
    """List all tasks."""
    conn = sqlite3.connect(DB_PATH)
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
