import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import AuthContext, require_admin, require_auth
from app.core.database import get_db_session
from app.core.files import save_user_document
from app.models.deleted_users_archive import DeletedUsersArchive
from app.models.distributor import Distributor
from app.models.user import User
from app.services.points import PointsService
from app.services.notifications import NotificationService
from app.services.users import (
    serialize_user_admin_list_item,
    serialize_user_profile,
    utc_now,
    validate_inn,
    validate_knd_number,
    write_admin_log,
)

router = APIRouter(prefix="/users", tags=["users"])


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    inn: str | None = Field(default=None, max_length=12)
    knd_1122035_number: str | None = Field(default=None, max_length=50)


class DeactivateUserRequest(BaseModel):
    is_active: bool


class AssignDistributorRequest(BaseModel):
    distributor_id: uuid.UUID | None = None


class AdminActivatePointsRequest(BaseModel):
    period_month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    comment: str | None = Field(default=None, max_length=500)


DocumentType = Literal["inn_photo", "knd_1122035_photo"]


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.scalar(
        select(User)
        .options(selectinload(User.distributor))
        .where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user


@router.get("/profile")
async def get_profile(auth: AuthContext = Depends(require_auth)) -> dict:
    return {"success": True, "data": serialize_user_profile(auth.user)}


@router.put("/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = auth.user

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip() or None
    if payload.first_name is not None:
        user.first_name = payload.first_name.strip() or None
    if payload.last_name is not None:
        user.last_name = payload.last_name.strip() or None
    if payload.middle_name is not None:
        user.middle_name = payload.middle_name.strip() or None

    if payload.inn is not None:
        if user.inn_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ИНН уже сохранён и не может быть изменён самостоятельно",
            )
        try:
            user.inn = validate_inn(payload.inn)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        user.inn_locked = True

    if payload.knd_1122035_number is not None:
        if user.knd_1122035_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Номер справки КНД уже сохранён и не может быть изменён самостоятельно",
            )
        try:
            user.knd_1122035_number = validate_knd_number(payload.knd_1122035_number)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        user.knd_1122035_locked = True

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ИНН уже используется другим пользователем",
        ) from exc

    return {"success": True, "data": serialize_user_profile(user)}


@router.post("/upload-document")
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = auth.user

    if document_type == "inn_photo":
        if user.inn_document_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Фото свидетельства ИНН уже загружено и не может быть заменено",
            )
        stored_path = await save_user_document(upload=file, subdirectory="documents/inn")
        user.inn_document_path = stored_path
    else:
        if user.knd_1122035_document_path:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Фото справки КНД уже загружено и не может быть заменено",
            )
        stored_path = await save_user_document(upload=file, subdirectory="documents/knd")
        user.knd_1122035_document_path = stored_path

    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "data": {
            "document_type": document_type,
            "path": stored_path,
            "profile": serialize_user_profile(user),
        },
    }


@router.get("/all")
async def list_users(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    users = (
        await db.scalars(
            select(User)
            .options(selectinload(User.distributor))
            .order_by(User.created_at.desc())
        )
    ).all()
    return {
        "success": True,
        "data": [serialize_user_admin_list_item(user) for user in users],
    }


@router.put("/{user_id}/verify-inn")
async def verify_inn(
    user_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = await _get_user_or_404(db, user_id)

    if not user.inn or not user.inn_document_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для подтверждения ИНН пользователь должен указать ИНН и загрузить документ",
        )

    old_value = {
        "inn_verified_by_admin": user.inn_verified_by_admin,
        "inn_verified_at": user.inn_verified_at.isoformat() if user.inn_verified_at else None,
    }
    user.inn_verified_by_admin = True
    user.inn_verified_at = utc_now()

    await write_admin_log(
        db,
        admin=auth.user,
        action="verify_inn",
        entity_type="user",
        entity_id=user.id,
        old_value=old_value,
        new_value={
            "inn_verified_by_admin": True,
            "inn_verified_at": user.inn_verified_at.isoformat(),
        },
    )
    await NotificationService(db).send(
        user_id=user.id,
        event_type="inn_verified",
        commit=False,
    )
    await db.commit()
    await db.refresh(user)

    return {"success": True, "data": serialize_user_profile(user)}


@router.put("/{user_id}/verify-self-employed")
async def verify_self_employed(
    user_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = await _get_user_or_404(db, user_id)

    if not user.knd_1122035_number or not user.knd_1122035_document_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для подтверждения самозанятости нужны номер и фото справки КНД 1122035",
        )

    old_value = {
        "is_self_employed": user.is_self_employed,
        "self_employed_verified_at": (
            user.self_employed_verified_at.isoformat() if user.self_employed_verified_at else None
        ),
    }
    user.is_self_employed = True
    user.self_employed_verified_at = utc_now()

    await write_admin_log(
        db,
        admin=auth.user,
        action="verify_self_employed",
        entity_type="user",
        entity_id=user.id,
        old_value=old_value,
        new_value={
            "is_self_employed": True,
            "self_employed_verified_at": user.self_employed_verified_at.isoformat(),
        },
    )
    await NotificationService(db).send(
        user_id=user.id,
        event_type="self_employed_verified",
        commit=False,
    )
    await db.commit()
    await db.refresh(user)

    return {"success": True, "data": serialize_user_profile(user)}


@router.put("/{user_id}/distributor")
async def assign_distributor(
    user_id: uuid.UUID,
    payload: AssignDistributorRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = await _get_user_or_404(db, user_id)

    old_value = {
        "distributor_id": str(user.distributor_id) if user.distributor_id else None,
        "distributor_name": user.distributor.name if user.distributor else None,
    }

    if payload.distributor_id is None:
        user.distributor_id = None
    else:
        distributor = await db.scalar(
            select(Distributor).where(Distributor.id == payload.distributor_id)
        )
        if distributor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Дистрибьютор не найден",
            )
        user.distributor_id = distributor.id

    await write_admin_log(
        db,
        admin=auth.user,
        action="assign_distributor",
        entity_type="user",
        entity_id=user.id,
        old_value=old_value,
        new_value={
            "distributor_id": str(user.distributor_id) if user.distributor_id else None,
            "distributor_name": user.distributor.name if user.distributor else None,
        },
    )
    await db.commit()
    user = await _get_user_or_404(db, user_id)

    return {"success": True, "data": serialize_user_profile(user)}


@router.put("/{user_id}/activate-points")
async def admin_activate_points(
    user_id: uuid.UUID,
    payload: AdminActivatePointsRequest | None = None,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    await _get_user_or_404(db, user_id)
    service = PointsService(db)
    try:
        result = await service.admin_activate_points(
            user_id=user_id,
            admin_id=auth.user.id,
            period_month=payload.period_month if payload else None,
            comment=payload.comment if payload else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await write_admin_log(
        db,
        admin=auth.user,
        action="admin_activate_points",
        entity_type="user",
        entity_id=user_id,
        old_value=None,
        new_value=result,
    )
    await db.commit()

    return {"success": True, "data": result}


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: uuid.UUID,
    payload: DeactivateUserRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = await _get_user_or_404(db, user_id)

    if user.id == auth.user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя деактивировать собственную учётную запись администратора",
        )

    old_value = {"is_active": user.is_active}
    user.is_active = payload.is_active

    await write_admin_log(
        db,
        admin=auth.user,
        action="deactivate_user" if not payload.is_active else "activate_user",
        entity_type="user",
        entity_id=user.id,
        old_value=old_value,
        new_value={"is_active": user.is_active},
    )
    await db.commit()
    await db.refresh(user)

    return {"success": True, "data": serialize_user_profile(user)}


@router.put("/{user_id}/documents")
async def admin_update_documents(
    user_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    inn: str | None = Form(default=None),
    knd_1122035_number: str | None = Form(default=None),
    inn_photo: UploadFile | None = File(default=None),
    knd_1122035_photo: UploadFile | None = File(default=None),
) -> dict:
    user = await _get_user_or_404(db, user_id)

    old_value = {
        "inn": user.inn,
        "inn_document_path": user.inn_document_path,
        "knd_1122035_number": user.knd_1122035_number,
        "knd_1122035_document_path": user.knd_1122035_document_path,
    }

    if inn is not None:
        try:
            user.inn = validate_inn(inn)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if knd_1122035_number is not None:
        try:
            user.knd_1122035_number = validate_knd_number(knd_1122035_number)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if inn_photo is not None and inn_photo.filename:
        user.inn_document_path = await save_user_document(
            upload=inn_photo,
            subdirectory="documents/inn",
        )

    if knd_1122035_photo is not None and knd_1122035_photo.filename:
        user.knd_1122035_document_path = await save_user_document(
            upload=knd_1122035_photo,
            subdirectory="documents/knd",
        )

    new_value = {
        "inn": user.inn,
        "inn_document_path": user.inn_document_path,
        "knd_1122035_number": user.knd_1122035_number,
        "knd_1122035_document_path": user.knd_1122035_document_path,
    }

    await write_admin_log(
        db,
        admin=auth.user,
        action="update_user_documents",
        entity_type="user",
        entity_id=user.id,
        old_value=old_value,
        new_value=new_value,
    )

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ИНН уже используется другим пользователем",
        ) from exc

    return {"success": True, "data": serialize_user_profile(user)}


@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = await _get_user_or_404(db, user_id)

    if user.role.value == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить учётную запись администратора",
        )
    if user.id == auth.user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственную учётную запись",
        )

    archive = DeletedUsersArchive(
        original_user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        inn=user.inn,
        deleted_by=auth.user.id,
        deleted_by_email=auth.user.email,
        deleted_by_name=auth.user.full_name,
    )
    db.add(archive)

    deleted_suffix = str(user.id)
    user.email = f"deleted_{deleted_suffix}@deleted.local"
    user.phone = f"deleted_{deleted_suffix}"
    user.full_name = None
    user.first_name = None
    user.last_name = None
    user.middle_name = None
    user.inn = None
    user.inn_document_path = None
    user.inn_locked = False
    user.inn_verified_by_admin = False
    user.inn_verified_at = None
    user.knd_1122035_number = None
    user.knd_1122035_document_path = None
    user.knd_1122035_locked = False
    user.is_self_employed = False
    user.self_employed_verified_at = None
    user.bank_account = None
    user.is_active = False

    await write_admin_log(
        db,
        admin=auth.user,
        action="delete_user_fz152",
        entity_type="user",
        entity_id=user.id,
        old_value={
            "email": archive.email,
            "full_name": archive.full_name,
            "phone": archive.phone,
            "inn": archive.inn,
        },
        new_value={"email": user.email, "phone": user.phone},
    )

    await db.commit()

    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "message": "Персональные данные удалены, история сохранена",
        },
    }
