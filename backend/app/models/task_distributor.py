import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.distributor import Distributor
    from app.models.task import Task


class TaskDistributor(Base):
    __tablename__ = "task_distributors"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="RESTRICT", onupdate="CASCADE"),
        primary_key=True,
    )

    task: Mapped["Task"] = relationship("Task", back_populates="task_distributors")
    distributor: Mapped["Distributor"] = relationship("Distributor")
