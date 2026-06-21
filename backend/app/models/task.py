import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TaskSource, TaskType
from app.models.mixins import CreatedAtMixin

if TYPE_CHECKING:
    from app.models.task_distributor import TaskDistributor
    from app.models.user import User
    from app.models.user_task_acceptance import UserTaskAcceptance


class Task(Base, CreatedAtMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    period_month: Mapped[str] = mapped_column(String(7), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type", native_enum=False, length=30),
        nullable=False,
    )
    source: Mapped[TaskSource] = mapped_column(
        Enum(TaskSource, name="task_source", native_enum=False, length=20),
        nullable=False,
        default=TaskSource.admin,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    task_distributors: Mapped[list["TaskDistributor"]] = relationship(
        "TaskDistributor",
        back_populates="task",
    )
    acceptances: Mapped[list["UserTaskAcceptance"]] = relationship(
        "UserTaskAcceptance",
        back_populates="task",
    )
