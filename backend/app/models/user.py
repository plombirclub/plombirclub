import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.admin_setting import AdminSetting
    from app.models.distributor import Distributor


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=20),
        nullable=False,
        default=UserRole.user,
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    participant_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )
    participant_position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    personal_name_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    inn: Mapped[Optional[str]] = mapped_column(String(12), unique=True, nullable=True)
    inn_document_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    inn_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inn_verified_by_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inn_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    knd_1122035_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    knd_1122035_document_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    knd_1122035_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_self_employed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    self_employed_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    distributor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    agreements_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    agreements_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    temporary_password_changed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_registration_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    bank_account: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    distributor: Mapped[Optional["Distributor"]] = relationship(
        "Distributor",
        back_populates="users",
    )
    admin_settings: Mapped[list["AdminSetting"]] = relationship(
        "AdminSetting",
        back_populates="admin",
    )
