"""Rule REST API endpoints — CRUD + event-driven rule application."""

import json
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from app.api.v0.auth import require_api_key, require_jwt_bearer
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
from app.core.logging import get_logger

logger = get_logger(__name__)
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
        tags=data.tags,
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
        tags=rule.tags,
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
        tags=rule.tags,
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
    page: int = Query(1, ge=1),
    tags: list[str] | None = Query(None),
) -> RuleListResponse:
    return await uc.execute(limit=limit, page=page, tags=tags)


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
        tags=data.tags,
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
        tags=rule.tags,
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
    auth: dict = Depends(require_jwt_bearer),
) -> dict:
    """Apply a single active rule matching the given rule_id or event_code.

    An end-user's own JWT can only report events about themselves: user_id
    and role are taken from the verified token, never from the request
    body, and dynamic_amount (unbounded, admin/service-granted rewards like
    BONUS/COMPETITION_BONUS) is rejected outright for this caller class.
    Only a trusted service caller (x-api-key) may act on behalf of an
    arbitrary user_id/role or use dynamic_amount.
    """
    sub = auth.get("sub")
    if sub is not None:
        user_id = uuid.UUID(sub)
        role = auth.get("role") or "simple"
        if "dynamic_amount" in (body.metadata or {}):
            raise HTTPException(
                status_code=403,
                detail="dynamic_amount is not allowed for user-authenticated requests",
            )
    else:
        if body.user_id is None:
            raise HTTPException(status_code=422, detail="user_id is required")
        user_id = body.user_id
        role = body.role

    metadata = dict(body.metadata or {})
    logger.info(
        "apply rule body",
        rule_id=str(body.rule_id) if body.rule_id else None,
        event_code=body.event_code,
        user_id=str(user_id),
        metadata=metadata,
        role=role,
        event_id=str(body.event_id) if body.event_id else None,
    )
    if role:
        metadata["role"] = role
    if body.event_id:
        metadata["event_id"] = str(body.event_id)
    result = await uc.execute(
        rule_id=body.rule_id,
        event_code=body.event_code,
        user_id=user_id,
        metadata=metadata,
    )
    return {
        "applied_rule": result,
        "applied": bool(result and result.get("status") == "applied"),
        "pending": bool(result and result.get("status") == "pending_approval"),
    }


@router.get("/apply/{user_id}")
async def can_apply_rule(
    user_id: uuid.UUID,
    uc: FromDishka[ApplyRuleUseCase],
    rule_id: uuid.UUID | None = Query(None),
    event_code: str | None = Query(None),
    role: str | None = Query(None),
    event_id: uuid.UUID | None = Query(None),
    metadata_json: str | None = Query(
        None,
        description="Optional JSON object with metadata keys required by the rule",
    ),
) -> dict:
    """Check whether the given user can apply the specified rule right now."""
    if (rule_id is None) == (event_code is None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of rule_id or event_code.",
        )
    metadata: dict = {}
    if metadata_json:
        try:
            parsed = json.loads(metadata_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422, detail="metadata_json must be valid JSON"
            ) from exc
        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=422, detail="metadata_json must be a JSON object"
            )
        metadata = parsed

    if role:
        metadata["role"] = role
    if event_id:
        metadata["event_id"] = str(event_id)

    return await uc.can_apply(
        event_code=event_code,
        rule_id=rule_id,
        user_id=user_id,
        metadata=metadata,
    )


@router.post("/apply/batch", response_model=BatchApplyRuleResponse)
async def apply_rule_batch(
    uc: FromDishka[BatchApplyRuleUseCase],
    body: BatchApplyRuleRequest = Body(...),
    _: str = Depends(require_api_key),
) -> BatchApplyRuleResponse:
    """Trusted-service-only: applies rewards for a batch of *other* users,
    so it cannot be scoped to a single caller's own JWT identity."""
    payload = [item.model_dump(exclude_none=True) for item in body.items]
    result = await uc.execute(event_code=body.event_code, items=payload)
    return BatchApplyRuleResponse(**result)
