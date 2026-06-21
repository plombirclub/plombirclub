import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import VerificationMethod, VerificationTargetType
from app.models.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.request import Request
    from app.models.user import User


class VerificationCode(Base, CreatedAtMixin):
    __tablename__ = "verification_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    target_type: Mapped[VerificationTargetType] = mapped_column(
        Enum(
            VerificationTargetType,
            name="verification_target_type",
            native_enum=False,
            length=30,
        ),
        nullable=False,
    )
    target_value: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[VerificationMethod] = mapped_column(
        Enum(
            VerificationMethod,
            name="verification_method",
            native_enum=False,
            length=10,
        ),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    request: Mapped[Optional["Request"]] = relationship(
        "Request",
        back_populates="verification_codes",
        foreign_keys=[request_id],
    )
