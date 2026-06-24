import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_auth
from app.core.config import settings
from app.core.database import get_db_session
from app.core.rate_limit import hit_rate_limit, reset_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    generate_plain_verification_code,
    hash_password,
    hash_verification_code,
    verify_password,
)
from app.models.enums import VerificationMethod, VerificationTargetType
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.services.email import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AcceptAgreementsRequest(BaseModel):
    personal_data_accepted: bool
    program_rules_accepted: bool
    email_notifications_accepted: bool


class ForgotPasswordRequest(BaseModel):
    email: str


class SendSmsCodeRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)


class VerifySmsCodeRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    code: str = Field(min_length=6, max_length=6)


class VerifyEmailCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


def _calculate_registration_complete(user: User) -> bool:
    return bool(
        user.phone_verified
        and user.temporary_password_changed
        and user.agreements_accepted
    )


def _set_auth_cookies(response: Response, *, user: User) -> None:
    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token = create_refresh_token(str(user.id))
    csrf_token = generate_csrf_token(str(user.id))

    response.set_cookie(
        key=settings.jwt_access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.jwt_refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.jwt_access_cookie_name, path="/")
    response.delete_cookie(key=settings.jwt_refresh_cookie_name, path="/")
    response.delete_cookie(key=settings.csrf_cookie_name, path="/")


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits


async def _create_verification_code(
    *,
    db: AsyncSession,
    user: User,
    method: VerificationMethod,
    target_value: str,
) -> str:
    code = generate_plain_verification_code()
    verification = VerificationCode(
        user_id=user.id,
        request_id=None,
        target_type=VerificationTargetType.profile_phone,
        target_value=target_value,
        method=method,
        code_hash=hash_verification_code(code),
        attempts_count=0,
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.verification_code_ttl_seconds),
    )
    db.add(verification)
    await db.commit()
    return code


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    ip = request.client.host if request.client else "unknown"
    rate_key = f"login:{payload.email.lower()}:{ip}"

    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        blocked, retry_after = await hit_rate_limit(
            key=rate_key,
            limit=settings.login_rate_limit,
            window_seconds=settings.login_rate_window_seconds,
        )
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много неудачных попыток входа. Повторите через {retry_after} сек.",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    await reset_rate_limit(rate_key)
    _set_auth_cookies(response, user=user)

    return {
        "success": True,
        "data": {
            "user_id": str(user.id),
            "role": user.role.value,
            "is_registration_complete": user.is_registration_complete,
            "first_login_required": not user.is_registration_complete,
        },
    }


@router.post("/change_password")
async def change_password(
    payload: ChangePasswordRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    user = auth.user
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Текущий пароль указан неверно")

    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Новый пароль должен отличаться от текущего")

    user.password_hash = hash_password(payload.new_password)
    user.temporary_password_changed = True
    user.is_registration_complete = _calculate_registration_complete(user)
    await db.commit()

    return {
        "success": True,
        "data": {
            "temporary_password_changed": user.temporary_password_changed,
            "is_registration_complete": user.is_registration_complete,
        },
    }


@router.post("/accept_agreements")
async def accept_agreements(
    payload: AcceptAgreementsRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if not (
        payload.personal_data_accepted
        and payload.program_rules_accepted
        and payload.email_notifications_accepted
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для завершения первого входа нужно принять все обязательные согласия",
        )

    user = auth.user
    user.agreements_accepted = True
    user.agreements_accepted_at = datetime.now(UTC)
    user.is_registration_complete = _calculate_registration_complete(user)
    await db.commit()

    return {
        "success": True,
        "data": {
            "agreements_accepted": user.agreements_accepted,
            "agreements_accepted_at": user.agreements_accepted_at.isoformat(),
            "is_registration_complete": user.is_registration_complete,
        },
    }


@router.post("/send-sms-code")
async def send_sms_code(
    payload: SendSmsCodeRequest,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    normalized_phone = _normalize_phone(payload.phone)
    if len(normalized_phone) != 11 or not normalized_phone.startswith("7"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректный формат телефона РФ")

    auth.user.phone = normalized_phone

    rate_key = f"send-code:sms:{auth.user.id}:{normalized_phone}"
    blocked, retry_after = await hit_rate_limit(
        key=rate_key,
        limit=settings.code_send_rate_limit,
        window_seconds=settings.code_send_rate_window_seconds,
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Код уже отправлялся недавно. Повторите через {retry_after} сек.",
        )

    code = await _create_verification_code(
        db=db,
        user=auth.user,
        method=VerificationMethod.sms,
        target_value=normalized_phone,
    )
    ip = request.client.host if request.client else "unknown"

    response_data = {"sent_to": normalized_phone, "method": "sms", "ip": ip}
    if settings.app_env == "development":
        response_data["debug_code"] = code

    return {"success": True, "data": response_data}


@router.post("/verify-sms-code")
async def verify_sms_code(
    payload: VerifySmsCodeRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    normalized_phone = _normalize_phone(payload.phone)
    code_row = await db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.user_id == auth.user.id,
            VerificationCode.method == VerificationMethod.sms,
            VerificationCode.target_type == VerificationTargetType.profile_phone,
            VerificationCode.target_value == normalized_phone,
            VerificationCode.verified_at.is_(None),
        )
        .order_by(VerificationCode.created_at.desc())
        .limit(1)
    )
    if code_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Код подтверждения не найден")

    if code_row.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия кода истек")

    if code_row.attempts_count >= settings.verify_code_max_attempts:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Превышено число попыток ввода кода")

    if code_row.code_hash != hash_verification_code(payload.code):
        code_row.attempts_count += 1
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код")

    code_row.verified_at = datetime.now(UTC)
    auth.user.phone = normalized_phone
    auth.user.phone_verified = True
    auth.user.is_registration_complete = _calculate_registration_complete(auth.user)
    await db.commit()

    return {
        "success": True,
        "data": {
            "phone_verified": auth.user.phone_verified,
            "is_registration_complete": auth.user.is_registration_complete,
        },
    }


@router.post("/send-email-code")
async def send_email_code(
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if not auth.user.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала укажите номер телефона, затем подтвердите его кодом по email",
        )

    rate_key = f"send-code:email:{auth.user.id}:{auth.user.email}"
    blocked, retry_after = await hit_rate_limit(
        key=rate_key,
        limit=settings.code_send_rate_limit,
        window_seconds=settings.code_send_rate_window_seconds,
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Код уже отправлялся недавно. Повторите через {retry_after} сек.",
        )

    code = await _create_verification_code(
        db=db,
        user=auth.user,
        method=VerificationMethod.email,
        target_value=auth.user.email,
    )

    email_error = await EmailService(db).send_verification_code(
        to_email=auth.user.email,
        phone=auth.user.phone,
        code=code,
    )
    if email_error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось отправить код на email: {email_error}",
        )

    response_data = {"sent_to": auth.user.email, "method": "email"}
    if settings.app_env == "development":
        response_data["debug_code"] = code

    return {"success": True, "data": response_data}


@router.post("/verify-email-code")
async def verify_email_code(
    payload: VerifyEmailCodeRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    code_row = await db.scalar(
        select(VerificationCode)
        .where(
            VerificationCode.user_id == auth.user.id,
            VerificationCode.method == VerificationMethod.email,
            VerificationCode.target_type == VerificationTargetType.profile_phone,
            VerificationCode.target_value == auth.user.email,
            VerificationCode.verified_at.is_(None),
        )
        .order_by(VerificationCode.created_at.desc())
        .limit(1)
    )
    if code_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Код подтверждения не найден")

    if code_row.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия кода истек")

    if code_row.attempts_count >= settings.verify_code_max_attempts:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Превышено число попыток ввода кода")

    if code_row.code_hash != hash_verification_code(payload.code):
        code_row.attempts_count += 1
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код")

    code_row.verified_at = datetime.now(UTC)
    auth.user.phone_verified = True
    auth.user.is_registration_complete = _calculate_registration_complete(auth.user)
    await db.commit()

    return {
        "success": True,
        "data": {
            "phone_verified": auth.user.phone_verified,
            "is_registration_complete": auth.user.is_registration_complete,
        },
    }


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    ip = request.client.host if request.client else "unknown"
    rate_key = f"forgot-password:{payload.email.lower()}:{ip}"
    blocked, retry_after = await hit_rate_limit(
        key=rate_key,
        limit=settings.forgot_password_rate_limit,
        window_seconds=settings.forgot_password_rate_window_seconds,
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Слишком много запросов восстановления. Повторите через {retry_after} сек.",
        )

    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is not None and user.is_active:
        user_email = user.email
        generated_password = secrets.token_urlsafe(8)
        previous_password_hash = user.password_hash
        previous_temp_changed = user.temporary_password_changed
        previous_registration_complete = user.is_registration_complete

        user.password_hash = hash_password(generated_password)
        user.temporary_password_changed = False
        user.is_registration_complete = _calculate_registration_complete(user)

        email_error = await EmailService(db).send_forgot_password(
            to_email=user.email,
            temporary_password=generated_password,
        )
        if email_error:
            user.password_hash = previous_password_hash
            user.temporary_password_changed = previous_temp_changed
            user.is_registration_complete = previous_registration_complete
            await db.rollback()
            logger.warning(
                "forgot-password: письмо не отправлено для %s, пароль не изменён: %s",
                user_email,
                email_error,
            )
        else:
            await db.commit()

    data = {"message": "Если аккаунт существует, временный пароль отправлен на email"}

    return {"success": True, "data": data}


@router.post("/logout")
async def logout(
    response: Response,
    _: AuthContext = Depends(require_auth),
) -> dict:
    _clear_auth_cookies(response)
    return {"success": True, "data": {"message": "Вы вышли из аккаунта"}}
