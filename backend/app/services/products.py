import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.distributor import Distributor
from app.models.enums import ProductSource
from app.models.product import Product
from app.models.product_distributor import ProductDistributor
from app.models.user import User
from app.services.users import write_admin_log


def _serialize_product(product: Product, *, include_admin: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(product.id),
        "article": product.article,
        "name": product.name,
        "description": product.description,
        "image_url": product.image_url,
        "category": product.category,
        "product_kind": product.product_kind,
        "flavor": product.flavor,
        "composition": product.composition,
        "weight_volume": product.weight_volume,
        "sort_order": product.sort_order,
        "product_group": product.product_group,
        "brand": product.brand,
        "code": product.code,
        "unit_barcode": product.unit_barcode,
        "box_barcode": product.box_barcode,
        "unit_volume": product.unit_volume,
        "net_weight": product.net_weight,
        "pieces_per_box": product.pieces_per_box,
        "source": product.source.value,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }
    if include_admin:
        payload["is_active"] = product.is_active
        payload["distributor_ids"] = [
            str(link.distributor_id) for link in (product.product_distributors or [])
        ]
        payload["manual_overrides"] = product.manual_overrides or {}
    return payload


class ProductsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_products(
        self,
        *,
        user: User,
        page: int,
        limit: int,
        product_group: str | None = None,
    ) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)

        base_query = (
            select(Product)
            .options(selectinload(Product.product_distributors))
            .where(Product.is_active.is_(True))
            .order_by(Product.sort_order.asc(), Product.name.asc())
        )

        if product_group:
            base_query = base_query.where(Product.product_group == product_group)

        products = (await self.db.scalars(base_query)).all()
        filtered = [item for item in products if self._is_visible_for_user(item, user)]

        total_count = len(filtered)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit
        page_items = filtered[offset : offset + limit]

        groups = sorted(
            {item.product_group for item in filtered if item.product_group},
            key=lambda value: value.lower(),
        )

        return {
            "items": [_serialize_product(item) for item in page_items],
            "groups": groups,
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def get_product(self, *, user: User, product_id: uuid.UUID) -> dict[str, Any]:
        product = await self.db.scalar(
            select(Product)
            .options(selectinload(Product.product_distributors))
            .where(Product.id == product_id, Product.is_active.is_(True))
        )
        if product is None:
            raise LookupError("Товар не найден")
        if not self._is_visible_for_user(product, user):
            raise LookupError("Товар не найден")
        return _serialize_product(product)

    async def list_groups(self, *, user: User) -> list[str]:
        products = (
            await self.db.scalars(
                select(Product)
                .options(selectinload(Product.product_distributors))
                .where(Product.is_active.is_(True))
                .order_by(Product.product_group.asc(), Product.sort_order.asc())
            )
        ).all()
        groups = sorted(
            {
                item.product_group
                for item in products
                if item.product_group and self._is_visible_for_user(item, user)
            },
            key=lambda value: value.lower(),
        )
        return groups

    async def list_products_admin(
        self,
        *,
        page: int,
        limit: int,
        include_inactive: bool = False,
        product_group: str | None = None,
    ) -> dict[str, Any]:
        page = max(page, 1)
        limit = min(max(limit, 1), 100)

        conditions = []
        if not include_inactive:
            conditions.append(Product.is_active.is_(True))

        base_query = (
            select(Product)
            .options(selectinload(Product.product_distributors))
            .order_by(Product.sort_order.asc(), Product.name.asc())
        )
        count_query = select(func.count(Product.id))
        if conditions:
            base_query = base_query.where(*conditions)
            count_query = count_query.where(*conditions)
        if product_group:
            base_query = base_query.where(Product.product_group == product_group)
            count_query = count_query.where(Product.product_group == product_group)

        total_count = int((await self.db.scalar(count_query)) or 0)
        total_pages = max((total_count + limit - 1) // limit, 1)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * limit

        products = (
            await self.db.scalars(base_query.offset(offset).limit(limit))
        ).all()

        return {
            "items": [_serialize_product(item, include_admin=True) for item in products],
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "limit": limit,
            },
        }

    async def create_product(
        self,
        *,
        admin: User,
        article: str,
        name: str,
        description: str | None = None,
        image_url: str | None = None,
        category: str | None = None,
        product_kind: str | None = None,
        flavor: str | None = None,
        composition: str | None = None,
        weight_volume: str | None = None,
        sort_order: int = 0,
        product_group: str | None = None,
        brand: str | None = None,
        code: str | None = None,
        unit_barcode: str | None = None,
        box_barcode: str | None = None,
        unit_volume: str | None = None,
        net_weight: str | None = None,
        pieces_per_box: int | None = None,
        distributor_ids: list[uuid.UUID] | None = None,
    ) -> dict[str, Any]:
        normalized_article = article.strip()
        normalized_name = name.strip()
        if not normalized_article:
            raise ValueError("Артикул не может быть пустым")
        if not normalized_name:
            raise ValueError("Название не может быть пустым")

        existing = await self.db.scalar(
            select(Product.id).where(Product.article == normalized_article).limit(1)
        )
        if existing is not None:
            raise ValueError("Товар с таким артикулом уже существует")

        product = Product(
            article=normalized_article,
            name=normalized_name,
            description=(description or "").strip() or None,
            image_url=(image_url or "").strip() or None,
            category=(category or "").strip() or None,
            product_kind=(product_kind or "").strip() or None,
            flavor=(flavor or "").strip() or None,
            composition=(composition or "").strip() or None,
            weight_volume=(weight_volume or "").strip() or None,
            sort_order=sort_order,
            product_group=(product_group or "").strip() or None,
            brand=(brand or "").strip() or None,
            code=(code or "").strip() or None,
            unit_barcode=(unit_barcode or "").strip() or None,
            box_barcode=(box_barcode or "").strip() or None,
            unit_volume=(unit_volume or "").strip() or None,
            net_weight=(net_weight or "").strip() or None,
            pieces_per_box=pieces_per_box,
            source=ProductSource.manual,
            is_active=True,
        )
        self.db.add(product)
        await self.db.flush()

        if distributor_ids:
            await self._set_distributors(product, distributor_ids)

        serialized = _serialize_product(product, include_admin=True)
        await write_admin_log(
            self.db,
            admin=admin,
            action="create_product",
            entity_type="product",
            entity_id=product.id,
            new_value=serialized,
        )
        await self.db.commit()
        await self.db.refresh(product)
        return serialized

    async def update_product(
        self,
        *,
        admin: User,
        product_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        product = await self.db.scalar(
            select(Product)
            .options(selectinload(Product.product_distributors))
            .where(Product.id == product_id)
            .limit(1)
        )
        if product is None:
            raise LookupError("Товар не найден")

        old_value = _serialize_product(product, include_admin=True)
        text_fields = [
            "name", "description", "image_url", "category", "product_kind", "flavor",
            "composition", "weight_volume", "product_group", "brand", "code",
            "unit_barcode", "box_barcode", "unit_volume", "net_weight",
        ]
        for field in text_fields:
            if field in updates:
                value = updates[field]
                setattr(product, field, (str(value).strip() if value is not None else None) or None)

        if "sort_order" in updates and updates["sort_order"] is not None:
            product.sort_order = int(updates["sort_order"])
        if "pieces_per_box" in updates:
            product.pieces_per_box = updates["pieces_per_box"]
        if "is_active" in updates and updates["is_active"] is not None:
            product.is_active = bool(updates["is_active"])

        if product.source == ProductSource.manual and updates:
            overrides = dict(product.manual_overrides or {})
            for field in text_fields + ["sort_order", "pieces_per_box"]:
                if field in updates:
                    overrides[field] = True
            product.manual_overrides = overrides

        serialized = _serialize_product(product, include_admin=True)
        await write_admin_log(
            self.db,
            admin=admin,
            action="update_product",
            entity_type="product",
            entity_id=product.id,
            old_value=old_value,
            new_value=serialized,
        )
        await self.db.commit()
        await self.db.refresh(product)
        return serialized

    async def hide_product(self, *, admin: User, product_id: uuid.UUID) -> dict[str, Any]:
        product = await self.db.scalar(select(Product).where(Product.id == product_id).limit(1))
        if product is None:
            raise LookupError("Товар не найден")

        old_value = _serialize_product(product, include_admin=True)
        product.is_active = False
        serialized = _serialize_product(product, include_admin=True)
        await write_admin_log(
            self.db,
            admin=admin,
            action="hide_product",
            entity_type="product",
            entity_id=product.id,
            old_value=old_value,
            new_value=serialized,
        )
        await self.db.commit()
        await self.db.refresh(product)
        return serialized

    async def set_product_distributors(
        self,
        *,
        admin: User,
        product_id: uuid.UUID,
        distributor_ids: list[uuid.UUID],
    ) -> dict[str, Any]:
        product = await self.db.scalar(
            select(Product)
            .options(selectinload(Product.product_distributors))
            .where(Product.id == product_id)
            .limit(1)
        )
        if product is None:
            raise LookupError("Товар не найден")

        await self._set_distributors(product, distributor_ids)
        await write_admin_log(
            self.db,
            admin=admin,
            action="set_product_distributors",
            entity_type="product",
            entity_id=product.id,
            new_value={"distributor_ids": [str(item) for item in distributor_ids]},
        )
        await self.db.commit()
        await self.db.refresh(product)
        return _serialize_product(product, include_admin=True)

    async def _set_distributors(self, product: Product, distributor_ids: list[uuid.UUID]) -> None:
        if distributor_ids:
            distributors = (
                await self.db.scalars(select(Distributor).where(Distributor.id.in_(distributor_ids)))
            ).all()
            found_ids = {item.id for item in distributors}
            missing = [str(item) for item in distributor_ids if item not in found_ids]
            if missing:
                raise LookupError(f"Дистрибьюторы не найдены: {', '.join(missing)}")

        existing = list(product.product_distributors or [])
        for link in existing:
            await self.db.delete(link)
        await self.db.flush()

        for distributor_id in distributor_ids:
            self.db.add(
                ProductDistributor(product_id=product.id, distributor_id=distributor_id)
            )

    def _is_visible_for_user(self, product: Product, user: User) -> bool:
        links = product.product_distributors
        if not links:
            return True
        if user.distributor_id is None:
            return False
        return any(link.distributor_id == user.distributor_id for link in links)
