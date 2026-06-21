import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PointsLedgerStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.request import Request
    from app.models.user import User


class PointsLedger(Base, TimestampMixin):
    __tablename__ = "points_ledger"

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
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PointsLedgerStatus] = mapped_column(
        Enum(
            PointsLedgerStatus,
            name="points_ledger_status",
            native_enum=False,
            length=30,
        ),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requests.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    period_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    request: Mapped[Optional["Request"]] = relationship("Request", foreign_keys=[request_id])
