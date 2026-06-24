import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_log import AdminLog
from app.models.user import User


async def write_admin_log(
    db: AsyncSession,
    *,
    admin: User,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    old_value: Any = None,
    new_value: Any = None,
) -> None:
    db.add(
        AdminLog(
            admin_id=admin.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=json.dumps(old_value, ensure_ascii=False, default=str) if old_value is not None else None,
            new_value=json.dumps(new_value, ensure_ascii=False, default=str) if new_value is not None else None,
        )
    )


def serialize_user_profile(user: User) -> dict[str, Any]:
    distributor = user.distributor
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
        "participant_code": user.participant_code,
        "participant_position": user.participant_position,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "middle_name": user.middle_name,
        "personal_name_locked": user.personal_name_locked,
        "phone": user.phone,
        "inn": user.inn,
        "inn_document_path": user.inn_document_path,
        "inn_locked": user.inn_locked,
        "inn_verified_by_admin": user.inn_verified_by_admin,
        "inn_verified_at": user.inn_verified_at.isoformat() if user.inn_verified_at else None,
        "knd_1122035_number": user.knd_1122035_number,
        "knd_1122035_document_path": user.knd_1122035_document_path,
        "knd_1122035_locked": user.knd_1122035_locked,
        "is_self_employed": user.is_self_employed,
        "self_employed_verified_at": (
            user.self_employed_verified_at.isoformat() if user.self_employed_verified_at else None
        ),
        "self_employed_status_label": (
            "Самозанятый" if user.is_self_employed else "Статус самозанятого не подтвержден"
        ),
        "is_active": user.is_active,
        "distributor_id": str(user.distributor_id) if user.distributor_id else None,
        "distributor_name": distributor.name if distributor else None,
        "phone_verified": user.phone_verified,
        "agreements_accepted": user.agreements_accepted,
        "agreements_accepted_at": (
            user.agreements_accepted_at.isoformat() if user.agreements_accepted_at else None
        ),
        "temporary_password_changed": user.temporary_password_changed,
        "is_registration_complete": user.is_registration_complete,
        "bank_account": user.bank_account,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def serialize_user_admin_list_item(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
        "participant_code": user.participant_code,
        "participant_position": user.participant_position,
        "phone": user.phone,
        "inn": user.inn,
        "inn_document_path": user.inn_document_path,
        "inn_verified_by_admin": user.inn_verified_by_admin,
        "knd_1122035_number": user.knd_1122035_number,
        "knd_1122035_document_path": user.knd_1122035_document_path,
        "is_self_employed": user.is_self_employed,
        "is_active": user.is_active,
        "distributor_id": str(user.distributor_id) if user.distributor_id else None,
        "distributor_name": user.distributor.name if user.distributor else None,
        "is_registration_complete": user.is_registration_complete,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def validate_inn(inn: str) -> str:
    cleaned = inn.strip()
    if len(cleaned) != 12 or not cleaned.isdigit():
        raise ValueError("ИНН должен состоять ровно из 12 цифр")
    return cleaned


def validate_knd_number(number: str) -> str:
    cleaned = number.strip()
    if not cleaned or len(cleaned) > 20 or not cleaned.isdigit():
        raise ValueError("Номер справки КНД 1122035 должен содержать только цифры (до 20 символов)")
    return cleaned


def utc_now() -> datetime:
    return datetime.now(UTC)
