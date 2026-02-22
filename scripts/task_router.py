#!/usr/bin/env python3
"""
Task Router - Decomposes tasks and assigns to agents.
"""

import json
import sqlite3
import os
from typing import Dict, List, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'swarm.db')
DB_TIMEOUT = 30.0

class TaskRouter:
    """Routes tasks to appropriate agents based on decomposition."""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        self.cursor = self.conn.cursor()
    
    def decompose_task(self, task_description: str, team_types: List[str]) -> List[Dict]:
        """
        Decompose task into sub-tasks for each agent type.
        
        Simple rule-based decomposition:
        - architect: Design/planning tasks
        - code-writer: Implementation tasks
        - tester: Testing/validation tasks
        - code-reviewer: Review tasks
        - researcher: Research/investigation
        - debugger: Debugging/problem solving
        - documenter: Documentation tasks
        - optimizer: Optimization tasks
        """
        subtasks = []
        
        # Task analysis keywords
        task_lower = task_description.lower()
        
        for agent_type in team_types:
            if agent_type == "architect":
                subtasks.append({
                    "agent_type": "architect",
                    "task": f"Design architecture for: {task_description}",
                    "priority": 1,
                    "dependencies": [],
                    "output": "architecture.md"
                })
            
            elif agent_type == "code-writer":
                deps = ["architect"] if "architect" in team_types else []
                subtasks.append({
                    "agent_type": "code-writer",
                    "task": f"Implement: {task_description}",
                    "priority": 2,
                    "dependencies": deps,
                    "output": "implementation/"
                })
            
            elif agent_type == "tester":
                deps = ["code-writer"] if "code-writer" in team_types else []
                subtasks.append({
                    "agent_type": "tester",
                    "task": f"Write tests and validate: {task_description}",
                    "priority": 3,
                    "dependencies": deps,
                    "output": "tests/"
                })
            
            elif agent_type == "code-reviewer":
                deps = []
                if "code-writer" in team_types:
                    deps.append("code-writer")
                elif "tester" in team_types:
                    deps.append("tester")
                
                subtasks.append({
                    "agent_type": "code-reviewer",
                    "task": f"Review implementation of: {task_description}",
                    "priority": 4,
                    "dependencies": deps,
                    "output": "review.md"
                })
            
            elif agent_type == "researcher":
                subtasks.append({
                    "agent_type": "researcher",
                    "task": f"Research solutions for: {task_description}",
                    "priority": 1,
                    "dependencies": [],
                    "output": "research.md"
                })
            
            elif agent_type == "debugger":
                subtasks.append({
                    "agent_type": "debugger",
                    "task": f"Debug and fix issues in: {task_description}",
                    "priority": 1,
                    "dependencies": [],
                    "output": "fixes/"
                })
            
            elif agent_type == "documenter":
                deps = []
                if "code-writer" in team_types:
                    deps.append("code-writer")
                
                subtasks.append({
                    "agent_type": "documenter",
                    "task": f"Document: {task_description}",
                    "priority": 5,
                    "dependencies": deps,
                    "output": "docs/"
                })
            
            elif agent_type == "optimizer":
                deps = ["code-writer"] if "code-writer" in team_types else []
                subtasks.append({
                    "agent_type": "optimizer",
                    "task": f"Optimize performance of: {task_description}",
                    "priority": 4,
                    "dependencies": deps,
                    "output": "optimized/"
                })
        
        # Sort by priority
        subtasks.sort(key=lambda x: x["priority"])
        
        return subtasks
    
    def assign_tasks(self, task_id: str, subtasks: List[Dict]):
        """Assign subtasks to agents in database."""
        # Find all active agents for this task
        self.cursor.execute('''
            SELECT id, agent_type FROM agents
            WHERE task_id = ? AND status = 'active'
        ''', (task_id,))

        # Map agent_type -> agent_id
        available_agents = {}
        for row in self.cursor.fetchall():
            agent_id, agent_type = row
            if agent_type not in available_agents:
                available_agents[agent_type] = []
            available_agents[agent_type].append(agent_id)
            
        updates = []
        for subtask in subtasks:
            agent_type = subtask["agent_type"]
            # Check if we have an agent for this subtask
            if agent_type in available_agents and available_agents[agent_type]:
                # Pick the first available agent of this type
                agent_id = available_agents[agent_type][0]
                
                updates.append((json.dumps(subtask), agent_id))
                print(f"  Assigned to {subtask['agent_type']}: {subtask['task'][:50]}...")
        
        # Batch update all agents
        if updates:
            self.cursor.executemany('''
                UPDATE agents
                SET result = ?
                WHERE id = ?
            ''', updates)

        self.conn.commit()
    
    def get_execution_order(self, task_id: str) -> List[Tuple[str, str]]:
        """Get execution order based on dependencies."""
        self.cursor.execute('''
            SELECT a.agent_type, a.result 
            FROM agents a
            WHERE a.task_id = ?
            ORDER BY a.spawned_at
        ''', (task_id,))
        
        agents = self.cursor.fetchall()
        
        # Build dependency graph
        order = []
        completed = set()
        
        for agent_type, result_json in agents:
            if result_json:
                subtask = json.loads(result_json)
                deps = subtask.get("dependencies", [])
                
                # Check if dependencies are satisfied
                if all(dep in completed for dep in deps):
                    order.append((agent_type, subtask["task"]))
                    completed.add(agent_type)
                else:
                    # Add to end of queue
                    order.append((agent_type, subtask["task"]))
        
        return order
    
    def close(self):
        self.conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Task Router')
    parser.add_argument('--task-id', required=True, help='Task ID')
    parser.add_argument('--decompose', action='store_true', help='Decompose task')
    
    args = parser.parse_args()
    
    router = TaskRouter()
    
    if args.decompose:
        # Get task info
        conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
        c = conn.cursor()
        
        c.execute('SELECT description, team_config FROM tasks WHERE id = ?', (args.task_id,))
        task = c.fetchone()
        conn.close()
        
        if task:
            description = task[0]
            team_types = json.loads(task[1])
            
            print(f"\n🔀 Decomposing task: {description}")
            print(f"Team: {', '.join(team_types)}")
            print("\nSub-tasks:")
            
            subtasks = router.decompose_task(description, team_types)
            for i, subtask in enumerate(subtasks, 1):
                print(f"  {i}. [{subtask['agent_type']}] {subtask['task'][:50]}...")
                if subtask['dependencies']:
                    print(f"     Depends on: {', '.join(subtask['dependencies'])}")
            
            router.assign_tasks(args.task_id, subtasks)
            print("\n✅ Tasks assigned to agents")
        else:
            print(f"Task {args.task_id} not found")
    
    router.close()


if __name__ == '__main__':
    main()
