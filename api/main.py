import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.routes import tasks, agents, ws
from scripts.db_migrations import apply_migrations
from scripts.observability import metrics
from scripts.orchestrator import setup_logging, SHUTDOWN_REQUESTED
import scripts.orchestrator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    apply_migrations()
    # metrics.start_server() # Optional
    yield
    # Shutdown
    scripts.orchestrator.SHUTDOWN_REQUESTED = True

app = FastAPI(title="Agent Swarm API", version="1.0.0", lifespan=lifespan)

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(ws.router, prefix="/ws", tags=["ws"])

@app.get("/")
async def root():
    return {"message": "Welcome to Agent Swarm API"}
