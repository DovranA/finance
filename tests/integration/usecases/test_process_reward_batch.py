import pytest
import uuid
from unittest.mock import AsyncMock
from app.usecases.process_reward_batch import ProcessRewardBatchUseCase
from app.domain.entities.reward_batch import RewardBatch
from app.domain.entities.account import Account

@pytest.mark.asyncio
async def test_process_reward_batch_success(mock_pool, mock_conn, mocker):
    # Setup mocks
    mock_account_repo = AsyncMock()
    mock_ledger_repo = AsyncMock()
    mock_reward_batch_repo = AsyncMock()
    mock_treasury_repo = AsyncMock()
    mock_outbox_repo = AsyncMock()
    mock_cache = AsyncMock()
    
    publisher_id = uuid.uuid4()
    content_id = uuid.uuid4()
    batch = RewardBatch(
        id=uuid.uuid4(),
        content_id=content_id,
        publisher_id=publisher_id,
        action_code="LIKE",
        total_publisher_reward=1000,
        total_platform_fee=100,
        total_treasury_cut=50,
        action_count=10,
        is_processed=False
    )
    
    mock_reward_batch_repo.fetch_unprocessed_for_update.return_value = [batch]
    mock_account_repo.get_or_create_by_user_id.return_value = Account.create(publisher_id)
    
    use_case = ProcessRewardBatchUseCase(
        pool=mock_pool,
        account_repo=mock_account_repo,
        ledger_repo=mock_ledger_repo,
        reward_batch_repo=mock_reward_batch_repo,
        treasury_repo=mock_treasury_repo,
        outbox_repo=mock_outbox_repo,
        cache=mock_cache
    )
    
    # Execute
    processed = await use_case.execute(batch_size=1)
    
    # Verify
    assert processed == 1
    mock_account_repo.get_or_create_by_user_id.assert_called_once_with(publisher_id, mock_conn)
    assert mock_ledger_repo.append.call_count == 3  # Publisher, Platform, Treasury
    mock_treasury_repo.credit.assert_called()
    mock_reward_batch_repo.mark_processed.assert_called_once_with(batch.id, mock_conn)
    mock_outbox_repo.insert.assert_called_once()
