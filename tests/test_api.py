import os
import pytest

# Set env var before importing app
os.environ["SWARM_DB"] = "test_api.db"

from fastapi.testclient import TestClient
from api.main import app

# Fixture to manage client lifecycle and DB cleanup
@pytest.fixture(scope="module")
def client():
    # Setup
    if os.path.exists("test_api.db"):
        os.remove("test_api.db")

    with TestClient(app) as c:
        yield c

    # Teardown
    if os.path.exists("test_api.db"):
        os.remove("test_api.db")

def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Agent Swarm API"}

def test_list_tasks(client):
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_agents(client):
    response = client.get("/agents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
