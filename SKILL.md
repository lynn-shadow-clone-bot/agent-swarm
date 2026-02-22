---
name: agent-swarm
description: Multi-Agent Team Orchestrator for complex tasks. Use when you need to assemble a team of specialized AI agents to collaboratively solve problems, write code, research, or complete multi-step projects. The skill provides pre-defined agent templates, team assembly workflow, and orchestration until 100% task completion. Triggers: 'assemble a team', 'multi-agent', 'agent team for', 'orchestrate agents', 'parallel agents', 'collaborative task'.
---

# Agent Swarm - Multi-Agent Team Orchestrator

Coordinate teams of specialized AI agents to solve complex tasks collaboratively.

## Quick Start

```bash
# Assemble a team and assign task
python3 scripts/orchestrator.py --task "Build a login system" --team "code-writer,tester,reviewer"
```

## Jules CLI Integration (NEW)

For complex feature development, use Jules CLI (required for private repos):

```bash
# Start a Jules session for new features
jules remote new --repo lynn-shadow-clone-bot/agent-swarm --session "Phase X: Feature Description"

# Monitor session
jules remote list --session

# Pull results when complete
jules remote pull --session <ID> --apply
```

**Note:** Private repos (like KyungiKyu/tasklist-app) require CLI - API integration only works for public repos.

## Bombenfest Implementation Phases

See `/tmp/bombenfest-plan.md` for full specification.

| Phase | Status | Features |
|-------|--------|----------|
| **1: Foundation** | ✅ Complete | Config Management (YAML+Pydantic), DB Hardening (WAL), Real OpenClaw Integration, Structured Logging |
| **2: Resilience** | ✅ Complete | Retry-Policy (Exponential Backoff + Jitter), Error Handling, Connection Rollback |
| **3: Observability** | 🔄 Ready | Metrics, Execution Tracing, Health Checks, Alerting |
| **4: Scalability** | ⏳ Pending | Async/Await, Connection Pooling, Task Prioritization |
| **5: Security** | ⏳ Pending | Secrets Management, Input Validation, Rate Limiting |
| **6: Testing** | 🔄 Partial | Unit Tests (3/3 passing), Integration Tests, Load Tests |
| **7: API & Polish** | ⏳ Pending | REST API, WebSocket, CLI Improvements |

## Agent Templates

Pre-defined agents in `references/AGENT_TEMPLATES.md`:

| Agent | Role | Best For |
|-------|------|----------|
| **code-writer** | Implementation | Writing code, creating files |
| **code-reviewer** | Quality | Reviewing code, finding issues |
| **researcher** | Discovery | Web search, documentation |
| **debugger** | Problem Solving | Finding bugs, analyzing errors |
| **tester** | Validation | Writing tests, QA |
| **architect** | Design | System design, planning |
| **documenter** | Documentation | Writing docs, comments |
| **optimizer** | Performance | Optimization, refactoring |

## Configuration

Edit `config.yaml`:

```yaml
database:
  path: ./swarm.db
  timeout: 30.0
  enable_wal: true

logging:
  level: INFO
  file: logs/swarm.log
  max_bytes: 10485760
  backup_count: 10

openclaw:
  gateway: http://127.0.0.1:18789
  retries: 3
```

Environment overrides: `SWARM_DB`, `OPENCLAW_GATEWAY`, `LOG_LEVEL`

## Workflow

### 1. Assemble Team

Select agents based on task requirements:

```python
# Example: Code feature with testing
team = ["code-writer", "tester", "code-reviewer"]

# Example: Research task
team = ["researcher", "documenter"]

# Example: Debug production issue
team = ["debugger", "code-reviewer", "architect"]
```

### 2. Clarify with Orchestrator

The orchestrator will ask clarifying questions before starting:

- Task scope and boundaries
- Expected output format
- Constraints and requirements
- Success criteria

### 3. Execute

Orchestrator coordinates agents:
- Distributes sub-tasks
- Manages dependencies
- Handles agent communication
- Monitors progress
- **NEW:** Automatic retry with exponential backoff on failures

### 4. Completion

Team reports back when:
- All sub-tasks completed
- Quality checks passed
- 100% of requirements met

## Team Composition Patterns

### Pattern: Feature Implementation
```
code-writer → tester → code-reviewer
```

### Pattern: Bug Fix
```
debugger → code-writer → tester → code-reviewer
```

### Pattern: Research & Implement
```
researcher → architect → code-writer → tester
```

### Pattern: Optimization
```
optimizer → tester → code-reviewer
```

## Commands

### Start Team
```bash
python3 scripts/orchestrator.py \
  --task "Implement JWT authentication" \
  --team "architect,code-writer,tester" \
  --output-dir ./output
```

### Check Status
```bash
python3 scripts/orchestrator.py --status --task-id <ID>
```

### Stop Team
```bash
python3 scripts/orchestrator.py --stop --task-id <ID>
```

### Run Tests
```bash
python3 -m unittest tests.test_utils -v
python3 -m unittest tests.test_orchestrator_failure -v
python3 -m unittest tests.test_config -v
```

## Jules Development Workflow

For implementing new phases:

```bash
# 1. Start Jules session
jules remote new --repo lynn-shadow-clone-bot/agent-swarm \
  --session "BOMBENFEST PHASE 3: Observability - Metrics & Health Checks"

# 2. Monitor progress
jules remote list --session

# 3. Review and pull when done
jules remote pull --session <ID> --apply

# 4. Test locally
python3 -m unittest discover tests/

# 5. Commit and push
git add .
git commit -m "feat: Phase 3 - Observability"
git push origin master
```

## Advanced Usage

### Custom Agent Configuration

Override defaults in task config:

```json
{
  "team": ["code-writer", "tester"],
  "agents": {
    "code-writer": {
      "model": "kimi-k2.5",
      "thinking": "high"
    }
  }
}
```

### Parallel Execution

```bash
python3 scripts/orchestrator.py \
  --task "Migrate database" \
  --team "architect,code-writer,tester" \
  --parallel \
  --max-agents 3
```

## Integration with OpenClaw

This skill integrates natively with OpenClaw's `sessions_spawn` for agent spawning:

- Agents run in isolated sessions
- Results reported back to orchestrator
- Native progress tracking via `subagents` tool
- **NEW:** Retry logic with exponential backoff for failed spawns

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Agent not responding | Check `sessions_list` for agent status |
| Task stuck | Use `--force-complete` to mark as done |
| Need more agents | Add to team and restart with `--resume` |
| Spawn fails | Automatic retry (3x) with exponential backoff |
| DB locked | WAL mode enabled - should not occur |
| Config not loading | Check `config.yaml` syntax, use env vars as fallback |

## References

- Agent Templates: See [AGENT_TEMPLATES.md](references/AGENT_TEMPLATES.md)
- Architecture: See [ARCHITECTURE.md](references/ARCHITECTURE.md)
- API Reference: See [API.md](references/API.md)
- Bombenfest Plan: See `/tmp/bombenfest-plan.md`
