import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, role: str) -> str:
    expire_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": expire_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire_at,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise ValueError("Недействительный токен") from exc
    return payload


def hash_verification_code(code: str) -> str:
    digest = hashlib.sha256(f"{settings.secret_key}:{code}".encode("utf-8")).hexdigest()
    return digest


def generate_plain_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def generate_csrf_token(user_id: str) -> str:
    nonce = secrets.token_urlsafe(16)
    issued_at = int(datetime.now(UTC).timestamp())
    payload = f"{user_id}:{nonce}:{issued_at}"
    signature = hmac.new(
        settings.csrf_secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    raw_value = f"{nonce}:{issued_at}:{signature}"
    return base64.urlsafe_b64encode(raw_value.encode("utf-8")).decode("utf-8")


def verify_csrf_token(token: str, user_id: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        nonce, issued_at, received_signature = decoded.split(":", 2)
    except (ValueError, UnicodeDecodeError):
        return False

    payload = f"{user_id}:{nonce}:{issued_at}"
    expected_signature = hmac.new(
        settings.csrf_secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(received_signature, expected_signature)
