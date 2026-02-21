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

## Troubleshooting

**Agent not responding:** Check `sessions_list` for agent status
**Task stuck:** Use `--force-complete` to mark as done
**Need more agents:** Add to team and restart with `--resume`

## References

- Agent Templates: See [AGENT_TEMPLATES.md](references/AGENT_TEMPLATES.md)
- Architecture: See [ARCHITECTURE.md](references/ARCHITECTURE.md)
- API Reference: See [API.md](references/API.md)
