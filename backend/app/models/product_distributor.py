import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.distributor import Distributor
    from app.models.product import Product


class ProductDistributor(Base):
    __tablename__ = "product_distributors"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="RESTRICT", onupdate="CASCADE"),
        primary_key=True,
    )

    product: Mapped["Product"] = relationship("Product", back_populates="product_distributors")
    distributor: Mapped["Distributor"] = relationship("Distributor")
