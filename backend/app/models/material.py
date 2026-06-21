import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MaterialContentType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user_material_progress import UserMaterialProgress


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[MaterialContentType] = mapped_column(
        Enum(
            MaterialContentType,
            name="material_content_type",
            native_enum=False,
            length=20,
        ),
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user_progress: Mapped[list["UserMaterialProgress"]] = relationship(
        "UserMaterialProgress",
        back_populates="material",
    )
