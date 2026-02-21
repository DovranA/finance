import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_balance_uc
from unittest.mock import AsyncMock

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_get_balance_uc():
    return AsyncMock()

def test_get_balance_success(client, mock_get_balance_uc):
    # Override dependency
    app.dependency_overrides[get_balance_uc] = lambda: mock_get_balance_uc
    
    user_id = uuid.uuid4()
    mock_get_balance_uc.execute.return_value = {
        "user_id": str(user_id),
        "account_id": str(uuid.uuid4()),
        "balance": 1000,
        "currency": "USD",
        "found": True,
        "cached": False
    }
    
    response = client.get(f"/accounts/{user_id}/balance")
    
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 1000
    assert data["user_id"] == str(user_id)
    
    # Clean up
    app.dependency_overrides.clear()

def test_get_balance_not_found(client, mock_get_balance_uc):
    app.dependency_overrides[get_balance_uc] = lambda: mock_get_balance_uc
    
    user_id = uuid.uuid4()
    mock_get_balance_uc.execute.return_value = {
        "user_id": str(user_id),
        "balance": 0,
        "currency": "USD",
        "found": False
    }
    
    response = client.get(f"/accounts/{user_id}/balance")
    
    assert response.status_code == 200
    assert response.json()["found"] is False
    
    app.dependency_overrides.clear()
