import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin
from app.core.database import get_db_session
from app.models.distributor import Distributor
from app.models.user import User
from app.services.users import write_admin_log

router = APIRouter(prefix="/distributors", tags=["distributors"])


class DistributorCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_active: bool = True


class DistributorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


def _serialize_distributor(distributor: Distributor) -> dict:
    return {
        "id": str(distributor.id),
        "name": distributor.name,
        "is_active": distributor.is_active,
        "created_at": distributor.created_at.isoformat() if distributor.created_at else None,
    }


@router.get("/")
async def list_distributors(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    distributors = (
        await db.scalars(select(Distributor).order_by(Distributor.name.asc()))
    ).all()
    return {
        "success": True,
        "data": [_serialize_distributor(item) for item in distributors],
    }


@router.post("/")
async def create_distributor(
    payload: DistributorCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    distributor = Distributor(
        name=payload.name.strip(),
        is_active=payload.is_active,
    )
    db.add(distributor)

    await write_admin_log(
        db,
        admin=auth.user,
        action="create_distributor",
        entity_type="distributor",
        entity_id=distributor.id,
        new_value=_serialize_distributor(distributor),
    )

    try:
        await db.commit()
        await db.refresh(distributor)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Дистрибьютор с таким названием уже существует",
        ) from exc

    return {"success": True, "data": _serialize_distributor(distributor)}


@router.put("/{distributor_id}")
async def update_distributor(
    distributor_id: uuid.UUID,
    payload: DistributorUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    distributor = await db.scalar(select(Distributor).where(Distributor.id == distributor_id))
    if distributor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Дистрибьютор не найден")

    old_value = _serialize_distributor(distributor)

    if payload.name is not None:
        distributor.name = payload.name.strip()
    if payload.is_active is not None:
        distributor.is_active = payload.is_active

    await write_admin_log(
        db,
        admin=auth.user,
        action="update_distributor",
        entity_type="distributor",
        entity_id=distributor.id,
        old_value=old_value,
        new_value=_serialize_distributor(distributor),
    )

    try:
        await db.commit()
        await db.refresh(distributor)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Дистрибьютор с таким названием уже существует",
        ) from exc

    return {"success": True, "data": _serialize_distributor(distributor)}
