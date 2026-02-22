from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from scripts.orchestrator import get_task_status_data
import asyncio
import json

router = APIRouter()

@router.websocket("/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        last_status = None
        while True:
            data = await get_task_status_data(task_id)
            if data:
                # Simple optimization: only send if changed
                # We need to serialize to compare, but data contains strings so it's fine.
                # However, ensure order is consistent.
                current_status = json.dumps(data, sort_keys=True)

                if current_status != last_status:
                    await websocket.send_json(data)
                    last_status = current_status

                if data['status'] in ['completed', 'failed']:
                    # We continue to poll to see if user wants to keep connection open,
                    # but maybe we can slow down polling.
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)
            else:
                await websocket.send_json({"error": "Task not found"})
                await asyncio.sleep(5)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
