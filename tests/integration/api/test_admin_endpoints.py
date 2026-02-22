import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from dishka import make_async_container, Provider, Scope, provide
from dishka.integrations.fastapi import setup_dishka

from app.main import create_app
from app.domain.entities.economic_action import EconomicAction
from app.usecases.admin_actions import (
    CreateEconomicActionUseCase,
    ListEconomicActionsUseCase,
)


def _make_test_app(mock_create_uc, mock_list_uc):
    """Create a test app with mocked admin use cases."""
    app = create_app()

    class MockProvider(Provider):
        scope = Scope.REQUEST

        @provide
        def create_action_uc(self) -> CreateEconomicActionUseCase:
            return mock_create_uc

        @provide
        def list_actions_uc(self) -> ListEconomicActionsUseCase:
            return mock_list_uc

    container = make_async_container(MockProvider())
    setup_dishka(container, app)

    return app


@pytest.fixture
def mock_create_action_uc():
    return AsyncMock()


@pytest.fixture
def mock_list_actions_uc():
    return AsyncMock()


@pytest.fixture
def client(mock_create_action_uc, mock_list_actions_uc):
    app = _make_test_app(mock_create_action_uc, mock_list_actions_uc)
    return TestClient(app)


def test_create_action_success(client, mock_create_action_uc):
    action_id = uuid.uuid4()
    mock_create_action_uc.execute.return_value = EconomicAction(
        id=action_id,
        code="LIKE",
        description="User likes a post",
        is_active=True,
    )

    payload = {"code": "LIKE", "description": "User likes a post"}
    response = client.post("/admin/actions", json=payload)

    assert response.status_code == 201
    assert response.json()["code"] == "LIKE"
    assert response.json()["id"] == str(action_id)


def test_list_actions(client, mock_list_actions_uc):
    mock_list_actions_uc.execute.return_value = [
        {"id": str(uuid.uuid4()), "code": "LIKE", "is_active": True, "versions": []}
    ]

    response = client.get("/admin/actions")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["code"] == "LIKE"
