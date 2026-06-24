import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import PrizeType
from app.models.mixins import TimestampMixin

# Фиксированный UUID системного приза СБП — совпадает с seed в миграции B.
SYSTEM_SBP_PRIZE_ID = uuid.UUID("a0000001-0000-4000-8000-000000000001")


class Prize(Base, TimestampMixin):
    __tablename__ = "prizes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[PrizeType] = mapped_column(
        Enum(PrizeType, name="prize_type", native_enum=False, length=20),
        nullable=False,
        default=PrizeType.certificate,
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
