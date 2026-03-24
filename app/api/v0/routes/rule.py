"""Rule REST API endpoints — CRUD + event-driven rule application."""

import uuid

from fastapi import APIRouter, Body, Query
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from app.api.v0.schemas.rule import (
    ApplyRuleRequest,
    BatchApplyRuleRequest,
    BatchApplyRuleResponse,
    CreateRuleRequest,
    UpdateRuleRequest,
    RuleResponse,
    RuleListResponse,
)
from app.usecases.rule_crud import (
    CreateRuleUseCase,
    GetRuleUseCase,
    ListRulesUseCase,
    UpdateRuleUseCase,
    DeleteRuleUseCase,
)
from app.usecases.apply_rule import ApplyRuleUseCase
from app.usecases.apply_rule_batch import BatchApplyRuleUseCase

router = APIRouter(prefix="/rules", tags=["Rules"], route_class=DishkaRoute)


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    uc: FromDishka[CreateRuleUseCase],
    data: CreateRuleRequest = Body(...),
) -> RuleResponse:
    rule = await uc.execute(
        event_code=data.event_code,
        conditions=data.conditions.model_dump(exclude_none=True),
        actions=data.actions.model_dump(exclude_none=True),
        description=data.description,
        description_i18n=(
            data.description_i18n.model_dump(exclude_none=True)
            if data.description_i18n
            else None
        ),
        priority=data.priority,
        expired_at=data.expired_at,
    )
    return RuleResponse(
        id=rule.id,
        event_code=rule.event_code,
        description_i18n=rule.description_i18n,
        conditions=rule.conditions,
        actions=rule.actions,
        priority=rule.priority,
        is_active=rule.is_active,
        expired_at=rule.expired_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: uuid.UUID,
    uc: FromDishka[GetRuleUseCase],
) -> RuleResponse:
    rule = await uc.execute(rule_id=rule_id)
    return RuleResponse(
        id=rule.id,
        event_code=rule.event_code,
        description_i18n=rule.description_i18n,
        conditions=rule.conditions,
        actions=rule.actions,
        priority=rule.priority,
        is_active=rule.is_active,
        expired_at=rule.expired_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get("", response_model=RuleListResponse)
async def list_rules(
    uc: FromDishka[ListRulesUseCase],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> RuleListResponse:
    rules = await uc.execute(limit=limit, offset=offset)
    return RuleListResponse(
        rules=[
            RuleResponse(
                id=r.id,
                event_code=r.event_code,
                description_i18n=r.description_i18n,
                conditions=r.conditions,
                actions=r.actions,
                priority=r.priority,
                is_active=r.is_active,
                expired_at=r.expired_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rules
        ],
        total=len(rules),
    )


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    uc: FromDishka[UpdateRuleUseCase],
    data: UpdateRuleRequest = Body(...),
) -> RuleResponse:
    rule = await uc.execute(
        rule_id=rule_id,
        event_code=data.event_code,
        conditions=data.conditions,
        actions=data.actions,
        description=data.description,
        description_i18n=(
            data.description_i18n.model_dump(exclude_none=True)
            if data.description_i18n
            else None
        ),
        priority=data.priority,
        is_active=data.is_active,
        expired_at=data.expired_at,
    )
    return RuleResponse(
        id=rule.id,
        event_code=rule.event_code,
        description_i18n=rule.description_i18n,
        conditions=rule.conditions,
        actions=rule.actions,
        priority=rule.priority,
        is_active=rule.is_active,
        expired_at=rule.expired_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: uuid.UUID,
    uc: FromDishka[DeleteRuleUseCase],
) -> dict:
    await uc.execute(rule_id=rule_id)
    return {"status": "deleted"}


@router.post("/apply")
async def apply_rule(
    uc: FromDishka[ApplyRuleUseCase],
    body: ApplyRuleRequest = Body(...),
) -> dict:
    """Apply a single active rule matching the given event_code to the account."""
    if body.role:
        body.metadata["role"] = body.role
    if body.event_id:
        body.metadata["event_id"] = body.event_id
    result = await uc.execute(
        event_code=body.event_code,
        user_id=body.user_id,
        metadata=body.metadata,
    )
    return {"applied_rule": result, "applied": result is not None}


@router.post("/apply/batch", response_model=BatchApplyRuleResponse)
async def apply_rule_batch(
    uc: FromDishka[BatchApplyRuleUseCase],
    body: BatchApplyRuleRequest = Body(...),
) -> BatchApplyRuleResponse:
    payload = [item.model_dump(exclude_none=True) for item in body.items]
    result = await uc.execute(event_code=body.event_code, items=payload)
    return BatchApplyRuleResponse(**result)
