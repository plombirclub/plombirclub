import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.models.enums import PrizeType
from app.services.rewards import RewardsService

router = APIRouter(prefix="/rewards", tags=["rewards"])


class RewardCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: PrizeType = PrizeType.certificate
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class RewardUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    type: PrizeType | None = None
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class RewardVisibilityRequest(BaseModel):
    distributor_ids: list[uuid.UUID] = Field(default_factory=list)


@router.get("/")
async def get_rewards(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = Query(default=False),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = RewardsService(db)
    data = await service.list_rewards(
        page=page,
        limit=limit,
        include_inactive=include_inactive,
        is_admin=auth.user.role.value == "admin",
        user_distributor_id=auth.user.distributor_id,
    )
    return {"success": True, "data": data}


@router.post("/")
async def create_reward(
    payload: RewardCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = RewardsService(db)
    try:
        data = await service.create_reward(
            admin=auth.user,
            name=payload.name,
            description=payload.description,
            prize_type=payload.type,
            image_url=payload.image_url,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.put("/{reward_id}")
async def update_reward(
    reward_id: uuid.UUID,
    payload: RewardUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = RewardsService(db)
    try:
        data = await service.update_reward(
            admin=auth.user,
            reward_id=reward_id,
            updates=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.delete("/{reward_id}")
async def hide_reward(
    reward_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = RewardsService(db)
    try:
        data = await service.hide_reward(
            admin=auth.user,
            reward_id=reward_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.get("/{reward_id}/visibility")
async def get_reward_visibility(
    reward_id: uuid.UUID,
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = RewardsService(db)
    try:
        data = await service.get_reward_visibility(reward_id=reward_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.put("/{reward_id}/visibility")
async def set_reward_visibility(
    reward_id: uuid.UUID,
    payload: RewardVisibilityRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = RewardsService(db)
    try:
        data = await service.set_system_reward_visibility(
            admin=auth.user,
            reward_id=reward_id,
            distributor_ids=payload.distributor_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"success": True, "data": data}
