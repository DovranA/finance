"""Admin REST API endpoints for economic action management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from app.api.schemas.schemas import (
    ActionResponse,
    ActivateVersionRequest,
    CreateActionRequest,
    CreateVersionRequest,
    VersionResponse,
)
from app.usecases.admin_actions import (
    ActivateEconomicVersionUseCase,
    CreateEconomicActionUseCase,
    CreateEconomicVersionUseCase,
    DisableEconomicActionUseCase,
    ListEconomicActionsUseCase,
)

router = APIRouter(prefix="/admin/actions", tags=["Admin"], route_class=DishkaRoute)


@router.post("", response_model=ActionResponse, status_code=201)
async def create_action(
    body: CreateActionRequest,
    uc: FromDishka[CreateEconomicActionUseCase],
):
    """Create a new dynamic action type."""
    try:
        action = await uc.execute(code=body.code, description=body.description)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ActionResponse(
        id=action.id,
        code=action.code,
        description=action.description,
        is_active=action.is_active,
        created_at=action.created_at,
    )


@router.post(
    "/{action_id}/new-version", response_model=VersionResponse, status_code=201
)
async def create_version(
    action_id: uuid.UUID,
    body: CreateVersionRequest,
    uc: FromDishka[CreateEconomicVersionUseCase],
):
    """Create a new reward version for an action."""
    try:
        version = await uc.execute(
            action_id=action_id,
            publisher_reward=body.publisher_reward,
            actor_reward=body.actor_reward,
            platform_fee=body.platform_fee,
            treasury_cut=body.treasury_cut,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return VersionResponse(
        id=version.id,
        version=version.version,
        publisher_reward=version.publisher_reward,
        actor_reward=version.actor_reward,
        platform_fee=version.platform_fee,
        treasury_cut=version.treasury_cut,
        is_active=version.is_active,
        active_from=version.active_from,
    )


@router.post("/{action_id}/activate", status_code=204)
async def activate_version(
    action_id: uuid.UUID,
    body: ActivateVersionRequest,
    uc: FromDishka[ActivateEconomicVersionUseCase],
):
    """Activate a specific version (deactivates all others for this action)."""
    try:
        await uc.execute(action_id=action_id, version_id=body.version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("")
async def list_actions(
    uc: FromDishka[ListEconomicActionsUseCase],
):
    """List all economic actions with their versions."""
    return await uc.execute()


@router.patch("/{action_id}/disable", status_code=204)
async def disable_action(
    action_id: uuid.UUID,
    uc: FromDishka[DisableEconomicActionUseCase],
):
    """Disable an economic action."""
    try:
        await uc.execute(action_id=action_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
