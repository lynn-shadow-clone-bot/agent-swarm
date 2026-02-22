from fastapi import APIRouter, HTTPException
from api.models import Agent
from typing import List
from scripts.orchestrator import db_query_all, db_query_one

router = APIRouter()

@router.get("/", response_model=List[Agent])
async def list_agents():
    agents = await db_query_all('SELECT id, agent_type, status, result, spawned_at, completed_at FROM agents ORDER BY spawned_at DESC')
    return [
        {
            "id": a[0],
            "type": a[1],
            "status": a[2],
            "result": a[3],
            "spawned_at": a[4],
            "completed_at": a[5]
        }
        for a in agents
    ]

@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    a = await db_query_one('SELECT id, agent_type, status, result, spawned_at, completed_at FROM agents WHERE id = ?', (agent_id,))
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "id": a[0],
        "type": a[1],
        "status": a[2],
        "result": a[3],
        "spawned_at": a[4],
        "completed_at": a[5]
    }
