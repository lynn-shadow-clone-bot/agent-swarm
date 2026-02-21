# Architecture

## System Overview

```
┌─────────────────────────────────────────────┐
│           Agent Swarm System                │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │  User Input  │──────▶  Orchestrator   │ │
│  └──────────────┘      └────────┬────────┘ │
│                                 │          │
│                    ┌────────────┴─────┐    │
│                    │   Task Router    │    │
│                    └────────┬─────────┘    │
│                             │              │
│         ┌───────────────────┼───────────┐  │
│         ▼                   ▼           ▼  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │ │
│  │(Writer)  │  │(Tester)  │  │(Reviewer)│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │             │             │       │
│       └─────────────┼─────────────┘       │
│                     ▼                     │
│            ┌──────────────┐               │
│            │  Consensus   │               │
│            └──────┬───────┘               │
│                   ▼                       │
│            ┌──────────────┐               │
│            │   Result     │               │
│            └──────────────┘               │
│                                             │
└─────────────────────────────────────────────┘
```

## Components

### 1. Orchestrator

**File:** `scripts/orchestrator.py`

**Responsibilities:**
- Parse user task
- Assemble team based on templates
- Ask clarifying questions
- Coordinate execution
- Monitor progress
- Report completion

**State Machine:**
```
IDLE → CLARIFYING → ASSEMBLING → EXECUTING → CONSENSUS → COMPLETE
         │               │             │           │
         └───────────────┴─────────────┴───────────┘
                        (on failure)
                              ▼
                          RETRY/ABORT
```

### 2. Task Router

**File:** `scripts/task_router.py`

**Responsibilities:**
- Decompose task into sub-tasks
- Assign sub-tasks to agents
- Manage dependencies
- Track completion

**Decomposition Strategy:**
1. Analyze task complexity
2. Identify parallelizable parts
3. Create dependency graph
4. Assign to agents

### 3. Agent Pool

**Responsibilities:**
- Spawn agents via `sessions_spawn`
- Monitor agent health
- Restart failed agents
- Collect results

**Agent Lifecycle:**
```
SPAWN → INITIALIZING → ACTIVE → WORKING → COMPLETED → DESTROY
   │         │            │        │          │
   └─────────┴────────────┴────────┴──────────┘
               (on failure)
                    ▼
                RESTART
```

### 4. Message Bus

**Implementation:** SQLite queue or in-memory

**Message Types:**
- `TASK_ASSIGN`: Assign task to agent
- `PROGRESS`: Agent progress update
- `QUESTION`: Agent needs clarification
- `RESULT`: Task completed
- `ERROR`: Agent failed

### 5. Consensus Engine

**Responsibilities:**
- Collect agent outputs
- Check for agreement
- Facilitate discussion
- Synthesize final result

**Consensus Algorithm:**
```python
def reach_consensus(agent_outputs):
    if all_agree(agent_outputs):
        return synthesize_agreement(agent_outputs)
    
    # Facilitate discussion
    discussion_rounds = 0
    while discussion_rounds < MAX_ROUNDS:
        # Agents review each other's work
        for agent in agents:
            agent.review(other_outputs)
        
        if all_agree(agent_outputs):
            return synthesize_agreement(agent_outputs)
        
        discussion_rounds += 1
    
    # Fallback: Orchestrator decides
    return orchestrator_decision(agent_outputs)
```

## Data Flow

### Task Execution Flow

```
1. User submits task
   └─▶ orchestrator.py --task "Build API"

2. Orchestrator clarifies requirements
   └─▶ Ask user questions
   └─▶ Define success criteria

3. Task Router decomposes
   └─▶ Sub-task 1: Design API
   └─▶ Sub-task 2: Implement endpoints
   └─▶ Sub-task 3: Write tests

4. Agent Pool spawns team
   └─▶ Spawn architect for design
   └─▶ Spawn code-writer for implementation
   └─▶ Spawn tester for tests

5. Agents execute in parallel
   └─▶ Each agent works on sub-task
   └─▶ Progress reported to Message Bus

6. Results collected
   └─▶ Consensus Engine validates
   └─▶ Discussion if needed

7. Final result delivered
   └─▶ Orchestrator reports to user
```

## Database Schema

### Tables

**tasks:**
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,
    config JSON
);
```

**agents:**
```sql
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    agent_type TEXT,
    status TEXT,
    session_key TEXT,
    spawned_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

**messages:**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT,
    message_type TEXT,
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Integration Points

### OpenClaw Integration

**sessions_spawn:**
```python
from openclaw import sessions_spawn

agent_session = sessions_spawn(
    task=subtask_description,
    agent_id="code-writer",
    label=f"agent-{task_id}-{agent_type}"
)
```

**sessions_send:**
```python
from openclaw import sessions_send

sessions_send(
    session_key=agent_session,
    message="Status update?"
)
```

**subagents:**
```python
from openclaw import subagents

# List all active agents
agents = subagents(action="list")
```

## Error Handling

### Agent Failure

1. Detect failure via heartbeat
2. Capture error message
3. Attempt restart (max 3 times)
4. If persistent, reassign task
5. Report to orchestrator

### Consensus Failure

1. If agents disagree after max rounds
2. Orchestrator makes executive decision
3. Log disagreement for review
4. Continue with best option

### Task Timeout

1. Set per-task timeout
2. Warn at 80% of timeout
3. Cancel at 100% timeout
4. Return partial results

## Performance Considerations

- **Parallelism:** Spawn agents concurrently
- **Resource Limits:** Max 10 agents per task
- **Timeouts:** Default 10 min per sub-task
- **Retries:** Max 3 retries per agent
- **Cleanup:** Auto-destroy completed agents
