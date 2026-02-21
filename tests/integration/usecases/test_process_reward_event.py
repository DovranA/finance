import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from app.usecases.process_reward_event import ProcessRewardEventUseCase
from app.infrastructure.rabbitmq.consumer import RewardEvent
from app.domain.entities.economic_action import EconomicActionVersion
from app.domain.entities.account import Account

@pytest.mark.asyncio
async def test_process_reward_event_success(mock_pool, mock_conn, mocker):
    # Setup mocks
    mock_account_repo = AsyncMock()
    mock_ledger_repo = AsyncMock()
    mock_actor_action_repo = AsyncMock()
    mock_economic_action_repo = AsyncMock()
    mock_reward_batch_repo = AsyncMock()
    mock_processed_event_repo = AsyncMock()
    mock_outbox_repo = AsyncMock()
    mock_cache = AsyncMock()
    
    # Configure mocks
    mock_cache.is_event_processed.return_value = False
    mock_processed_event_repo.exists.return_value = False
    
    action_id = uuid.uuid4()
    version_id = uuid.uuid4()
    mock_economic_action_repo.get_active_version.return_value = EconomicActionVersion(
        id=version_id,
        action_id=action_id,
        publisher_reward=100,
        actor_reward=50,
        platform_fee=10,
        treasury_cut=5,
        version=1,
        is_active=True,
        active_from=datetime.now(timezone.utc)
    )
    
    actor_id = uuid.uuid4()
    mock_account_repo.get_or_create_by_user_id.return_value = Account.create(actor_id)
    
    use_case = ProcessRewardEventUseCase(
        pool=mock_pool,
        account_repo=mock_account_repo,
        ledger_repo=mock_ledger_repo,
        actor_action_repo=mock_actor_action_repo,
        economic_action_repo=mock_economic_action_repo,
        reward_batch_repo=mock_reward_batch_repo,
        processed_event_repo=mock_processed_event_repo,
        outbox_repo=mock_outbox_repo,
        cache=mock_cache
    )
    
    event = RewardEvent(
        event_id=uuid.uuid4(),
        actor_id=actor_id,
        content_id=uuid.uuid4(),
        publisher_id=uuid.uuid4(),
        action_code="LIKE",
        timestamp="2024-01-01T00:00:00Z"
    )
    
    # Execute
    await use_case.execute(event)
    
    # Verify calls
    mock_actor_action_repo.create.assert_called_once()
    mock_ledger_repo.append.assert_called_once()
    mock_account_repo.update_balance.assert_called_once()
    mock_reward_batch_repo.upsert_batch.assert_called_once()
    mock_outbox_repo.insert.assert_called_once()
    mock_processed_event_repo.mark_processed.assert_called_once()
    mock_cache.mark_event_processed.assert_called_once()
