import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ProductSource
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.product_distributor import ProductDistributor


class Product(Base, TimestampMixin):
    """Таблица продукции. Поля — по разделу 10 ТЗ; схема не детализирована в разделе 14."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    article: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_kind: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    flavor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    composition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weight_volume: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_group: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit_barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    box_barcode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_volume: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    net_weight: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pieces_per_box: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[ProductSource] = mapped_column(
        Enum(ProductSource, name="product_source", native_enum=False, length=20),
        nullable=False,
        default=ProductSource.manual,
    )
    manual_overrides: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    product_distributors: Mapped[list["ProductDistributor"]] = relationship(
        "ProductDistributor",
        back_populates="product",
    )
