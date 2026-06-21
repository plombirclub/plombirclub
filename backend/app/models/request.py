import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RequestStatus, VerificationMethod
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.prize import Prize
    from app.models.user import User
    from app.models.verification_code import VerificationCode


class Request(Base, TimestampMixin):
    __tablename__ = "requests"

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
    prize_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prizes.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[RequestStatus] = mapped_column(
        Enum(
            RequestStatus,
            name="request_status",
            native_enum=False,
            length=30,
        ),
        nullable=False,
        default=RequestStatus.placed,
    )
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    points_spent: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    inn_verified_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False)
    knd_1122035_number_snapshot: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    self_employed_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payout_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payout_bank_account_snapshot: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    payout_details_changed_after_request: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    verification_method: Mapped[Optional[VerificationMethod]] = mapped_column(
        Enum(
            VerificationMethod,
            name="verification_method",
            native_enum=False,
            length=10,
        ),
        nullable=True,
    )
    verification_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    admin_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fulfillment_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    prize: Mapped["Prize"] = relationship("Prize", foreign_keys=[prize_id])
    verification_codes: Mapped[list["VerificationCode"]] = relationship(
        "VerificationCode",
        back_populates="request",
        foreign_keys="VerificationCode.request_id",
    )
