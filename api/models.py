from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class TaskCreate(BaseModel):
    description: str
    team_types: List[str]

class Agent(BaseModel):
    id: str
    type: str
    status: str
    result: Optional[str] = None
    spawned_at: Optional[str] = None
    completed_at: Optional[str] = None

class Task(BaseModel):
    id: str
    description: str
    status: str
    result: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    team_config: List[str]
    agents: List[Agent] = []

class TaskList(BaseModel):
    id: str
    description: str
    status: str
    created_at: str
