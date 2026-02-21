import pytest
import uuid
from datetime import datetime, timezone
from app.domain.services.reward_engine import RewardEngine
from app.domain.entities.economic_action import EconomicActionVersion

def test_reward_engine_calculation():
    actor_id = uuid.uuid4()
    content_id = uuid.uuid4()
    actor_account_id = uuid.uuid4()
    
    config = EconomicActionVersion(
        id=uuid.uuid4(),
        action_id=uuid.uuid4(),
        publisher_reward=100,
        actor_reward=50,
        platform_fee=10,
        treasury_cut=5,
        version=1,
        is_active=True,
        active_from=datetime.now(timezone.utc)
    )
    
    calc = RewardEngine.calculate(
        actor_id=actor_id,
        content_id=content_id,
        action_code="LIKE",
        config=config,
        actor_account_id=actor_account_id
    )
    
    assert calc.actor_action.reward_amount == 50
    assert calc.publisher_reward == 100
    assert calc.platform_fee == 10
    assert calc.treasury_cut == 5
    
    # Check actor action
    assert calc.actor_action.actor_id == actor_id
    
    # Check ledger entry
    assert calc.actor_ledger_entry.account_id == actor_account_id
    assert calc.actor_ledger_entry.amount == 50
