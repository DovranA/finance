import datetime
import uuid

from fastapi import APIRouter
from dishka.integrations.fastapi import DishkaRoute, FromDishka

from app.infrastructure.rabbitmq.consumer import RewardEvent
from app.usecases.process_reward_batch import ProcessRewardBatchUseCase
from app.usecases.process_reward_event import ProcessRewardEventUseCase

router = APIRouter(prefix="/test", tags=["Test"], route_class=DishkaRoute)


@router.get("/batch")
async def batch_test(uc: FromDishka[ProcessRewardEventUseCase]):
    await uc.execute(
        event=RewardEvent(
            event_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            content_id=uuid.uuid4(),
            publisher_id=uuid.uuid4(),
            action_code="TEST_ACTION",
            timestamp=datetime.datetime.now(),
        )
    )
    return {"message": "Batch processing test successful"}
