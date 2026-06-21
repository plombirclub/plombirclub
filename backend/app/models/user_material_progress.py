import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MaterialProgressStatus

if TYPE_CHECKING:
    from app.models.material import Material
    from app.models.user import User


class UserMaterialProgress(Base):
    __tablename__ = "user_materials_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "material_id", name="uq_user_materials_progress_user_material"),
    )

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
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[MaterialProgressStatus] = mapped_column(
        Enum(
            MaterialProgressStatus,
            name="material_progress_status",
            native_enum=False,
            length=20,
        ),
        nullable=False,
        default=MaterialProgressStatus.not_started,
    )
    pages_viewed: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    total_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    material: Mapped["Material"] = relationship("Material", back_populates="user_progress")
