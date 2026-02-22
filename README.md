# Agent Swarm

A multi-agent team orchestrator capable of decomposing tasks, assembling teams, and executing complex workflows.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configuration:
   - Check `config.yaml` for database and logging settings.

## Usage

### CLI

Run the orchestrator:
```bash
python scripts/orchestrator.py --task "Build a simple calculator in Python" --team "code-writer,tester"
```

List tasks:
```bash
python scripts/orchestrator.py --list
```

Check status:
```bash
python scripts/orchestrator.py --status --task-id <TASK_ID>
```

### API

The project includes a REST API and WebSocket support. See [README_API.md](README_API.md) for details.
