from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.models import TaskCreate, Task, TaskList
from scripts.orchestrator import (
    assemble_team, spawn_agents, execute_task,
    ask_clarifying_questions, get_task_status_data, get_all_tasks
)
import asyncio
from typing import List

router = APIRouter()

async def process_task(task_id: str):
    # We might need to ensure DB connection is safe here or handled by the pool
    await spawn_agents(task_id)
    await execute_task(task_id)

@router.post("/", response_model=Task)
async def create_task(task_in: TaskCreate, background_tasks: BackgroundTasks):
    # Non-interactive clarifications
    clarifications = ask_clarifying_questions(task_in.description, interactive=False)

    try:
        # Assemble team
        task_id = await assemble_team(task_in.description, task_in.team_types, clarifications)

        # Start background processing
        background_tasks.add_task(process_task, task_id)

        # Return initial status
        data = await get_task_status_data(task_id)
        if not data:
             raise HTTPException(status_code=500, detail="Failed to create task")

        # Convert agents list of dicts to list of Pydantic models (implicit or manual?)
        # Pydantic should handle it if the keys match
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TaskList])
async def list_tasks_endpoint():
    return await get_all_tasks()

@router.get("/{task_id}", response_model=Task)
async def get_task_endpoint(task_id: str):
    data = await get_task_status_data(task_id)
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    return data
