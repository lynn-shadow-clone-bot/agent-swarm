# Agent Swarm API

REST API and WebSocket support for Agent Swarm.

## Running the API

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   - Access documentation at `http://localhost:8000/docs` (Swagger UI).
   - Access Redoc at `http://localhost:8000/redoc`.

## Endpoints

### Tasks

- `POST /tasks/`: Create a new task.
  - Body:
    ```json
    {
      "description": "Task description",
      "team_types": ["code-writer", "tester"]
    }
    ```
  - Returns: Task object with ID.

- `GET /tasks/`: List all tasks.

- `GET /tasks/{task_id}`: Get task status.

- `WS /ws/tasks/{task_id}`: WebSocket for real-time task updates.
  - Sends full task status JSON whenever it changes.
  - Polls every 2 seconds.

### Agents

- `GET /agents/`: List all agents.
- `GET /agents/{agent_id}`: Get agent details.

## WebSocket Example

Connect to `ws://localhost:8000/ws/tasks/{task_id}`.
Example (JS):
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/tasks/your-task-id");
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Status update:", data);
};
```
