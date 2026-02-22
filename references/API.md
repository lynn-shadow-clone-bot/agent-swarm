# API Reference

## Command Line Interface

### orchestrator.py

Main orchestrator for agent swarm coordination.

#### Commands

**Start New Task**
```bash
python3 scripts/orchestrator.py \
  --task "Implement JWT authentication" \
  --team "architect,code-writer,tester" \
  --output-dir ./output
```

Options:
- `--task`: Task description (required)
- `--team`: Comma-separated agent types (required)
- `--output-dir`: Output directory (default: ./output)

**Check Task Status**
```bash
python3 scripts/orchestrator.py --status --task-id <UUID>
```

**List All Tasks**
```bash
python3 scripts/orchestrator.py --list
```

### task_router.py

Task decomposition and routing.

#### Commands

**Decompose Task**
```bash
python3 scripts/task_router.py --task-id <UUID> --decompose
```

## Database API

### Tables

#### tasks

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Task UUID |
| description | TEXT | Task description |
| status | TEXT | pending/assembling/executing/completed |
| team_config | TEXT | JSON array of agent types |
| created_at | TIMESTAMP | Creation time |
| completed_at | TIMESTAMP | Completion time |
| result | TEXT | Final result |
| output_dir | TEXT | Output directory path |

#### agents

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Agent UUID |
| task_id | TEXT | Parent task ID |
| agent_type | TEXT | Type (code-writer, tester, etc.) |
| status | TEXT | pending/active/working/completed |
| session_key | TEXT | OpenClaw session key |
| spawned_at | TIMESTAMP | Spawn time |
| completed_at | TIMESTAMP | Completion time |
| result | TEXT | Agent output |

#### messages

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Message ID |
| task_id | TEXT | Parent task ID |
| agent_id | TEXT | Source agent |
| message_type | TEXT | SPAWNED/PROGRESS/COMPLETED/ERROR |
| content | TEXT | Message content |
| timestamp | TIMESTAMP | Message time |

### Queries

**Get task status:**
```sql
SELECT status, result FROM tasks WHERE id = ?;
```

**Get agent statuses:**
```sql
SELECT agent_type, status FROM agents WHERE task_id = ?;
```

**Get messages:**
```sql
SELECT * FROM messages WHERE task_id = ? ORDER BY timestamp;
```

## Agent Templates

Load agent configuration:

```python
from scripts.orchestrator import load_agent_template

template = load_agent_template("code-writer")
# Returns: {
#   "agent_id": "code-writer",
#   "model": "kimi-coding/k2p5",
#   "thinking": "high",
#   "system_prompt": "..."
# }
```

## Integration with OpenClaw

### Spawn Agent

```python
from openclaw import sessions_spawn

agent_session = sessions_spawn(
    task=subtask_description,
    agent_id="code-writer",
    label=f"swarm-{task_id}-writer"
)
```

### Send Message to Agent

```python
from openclaw import sessions_send

sessions_send(
    session_key=agent_session,
    message="Your subtask is: implement login endpoint"
)
```

### Check Agent Status

```python
from openclaw import subagents

agents = subagents(action="list")
# Filter for swarm agents
swarm_agents = [a for a in agents if 'swarm' in a.get('label', '')]
```

## Workflow Integration

### Complete Workflow Example

```python
import subprocess
import json

# 1. Start orchestration
result = subprocess.run([
    'python3', 'scripts/orchestrator.py',
    '--task', 'Build login system',
    '--team', 'architect,code-writer,tester'
], capture_output=True, text=True)

# Extract task_id from output
task_id = extract_task_id(result.stdout)

# 2. Decompose task
subprocess.run([
    'python3', 'scripts/task_router.py',
    '--task-id', task_id,
    '--decompose'
])

# 3. Monitor progress
while True:
    result = subprocess.run([
        'python3', 'scripts/orchestrator.py',
        '--status', '--task-id', task_id
    ], capture_output=True, text=True)
    
    if 'completed' in result.stdout:
        break
    
    time.sleep(10)

# 4. Get results
conn = sqlite3.connect('swarm.db', timeout=30.0)
c = conn.cursor()
c.execute('SELECT result FROM tasks WHERE id = ?', (task_id,))
final_result = c.fetchone()[0]
```

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 1 | Invalid arguments | Check command syntax |
| 2 | Task not found | Verify task_id |
| 3 | Agent spawn failed | Check OpenClaw connection |
| 4 | Database error | Check swarm.db permissions |
| 5 | Timeout | Increase timeout or retry |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SWARM_DB` | `swarm.db` | Database path |
| `OPENCLAW_BIN` | `openclaw` | OpenClaw CLI path |
| `MAX_AGENTS` | `10` | Max concurrent agents |
| `AGENT_TIMEOUT` | `600` | Agent timeout (seconds) |
| `RETRY_ATTEMPTS` | `3` | Max retry attempts |
