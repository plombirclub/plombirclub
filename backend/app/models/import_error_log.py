import uuid
from typing import Optional

from sqlalchemy import Enum, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ImportType
from app.models.mixins import CreatedAtMixin


class ImportErrorLog(Base, CreatedAtMixin):
    __tablename__ = "import_error_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    import_type: Mapped[ImportType] = mapped_column(
        Enum(
            ImportType,
            name="import_type",
            native_enum=False,
            length=20,
        ),
        nullable=False,
    )
    row_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_row_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
