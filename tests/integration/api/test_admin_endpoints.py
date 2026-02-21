import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_create_action_uc, get_list_actions_uc
from unittest.mock import AsyncMock
from app.domain.entities.economic_action import EconomicAction

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_create_action_uc():
    return AsyncMock()

@pytest.fixture
def mock_list_actions_uc():
    return AsyncMock()

def test_create_action_success(client, mock_create_action_uc):
    app.dependency_overrides[get_create_action_uc] = lambda: mock_create_action_uc
    
    action_id = uuid.uuid4()
    mock_create_action_uc.execute.return_value = EconomicAction(
        id=action_id,
        code="LIKE",
        description="User likes a post",
        is_active=True
    )
    
    payload = {"code": "LIKE", "description": "User likes a post"}
    response = client.post("/admin/actions", json=payload)
    
    assert response.status_code == 201
    assert response.json()["code"] == "LIKE"
    assert response.json()["id"] == str(action_id)
    
    app.dependency_overrides.clear()

def test_list_actions(client, mock_list_actions_uc):
    app.dependency_overrides[get_list_actions_uc] = lambda: mock_list_actions_uc
    
    mock_list_actions_uc.execute.return_value = [
        {"id": str(uuid.uuid4()), "code": "LIKE", "is_active": True, "versions": []}
    ]
    
    response = client.get("/admin/actions")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["code"] == "LIKE"
    
    app.dependency_overrides.clear()
