import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from dishka import make_async_container, Provider, Scope, provide
from dishka.integrations.fastapi import setup_dishka

from app.main import create_app
from app.usecases.get_balance import GetBalanceUseCase


def _make_test_app(mock_uc):
    """Create a test app with a Dishka container that provides the mock use case."""
    app = create_app()

    class MockProvider(Provider):
        scope = Scope.REQUEST

        @provide
        def get_balance_uc(self) -> GetBalanceUseCase:
            return mock_uc

    # Replace the container set up by create_app
    container = make_async_container(MockProvider())
    setup_dishka(container, app)

    return app


@pytest.fixture
def mock_get_balance_uc():
    return AsyncMock()


@pytest.fixture
def client(mock_get_balance_uc):
    app = _make_test_app(mock_get_balance_uc)
    return TestClient(app)


def test_get_balance_success(client, mock_get_balance_uc):
    user_id = uuid.uuid4()
    mock_get_balance_uc.execute.return_value = {
        "user_id": str(user_id),
        "account_id": str(uuid.uuid4()),
        "balance": 1000,
        "currency": "USD",
        "found": True,
        "cached": False,
    }

    response = client.get(f"/accounts/{user_id}/balance")

    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 1000
    assert data["user_id"] == str(user_id)


def test_get_balance_not_found(client, mock_get_balance_uc):
    user_id = uuid.uuid4()
    mock_get_balance_uc.execute.return_value = {
        "user_id": str(user_id),
        "balance": 0,
        "currency": "USD",
        "found": False,
    }

    response = client.get(f"/accounts/{user_id}/balance")

    assert response.status_code == 200
    assert response.json()["found"] is False
