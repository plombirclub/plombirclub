import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin, require_registration_complete
from app.core.database import get_db_session
from app.services.products import ProductsService

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreateRequest(BaseModel):
    article: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=255)
    product_kind: str | None = Field(default=None, max_length=255)
    flavor: str | None = Field(default=None, max_length=255)
    composition: str | None = None
    weight_volume: str | None = Field(default=None, max_length=100)
    sort_order: int = 0
    product_group: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=100)
    unit_barcode: str | None = Field(default=None, max_length=50)
    box_barcode: str | None = Field(default=None, max_length=50)
    unit_volume: str | None = Field(default=None, max_length=50)
    net_weight: str | None = Field(default=None, max_length=50)
    pieces_per_box: int | None = None
    shelf_life: str | None = Field(default=None, max_length=100)
    nutrition_facts: str | None = None
    distributor_ids: list[uuid.UUID] = Field(default_factory=list)


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=255)
    product_kind: str | None = Field(default=None, max_length=255)
    flavor: str | None = Field(default=None, max_length=255)
    composition: str | None = None
    weight_volume: str | None = Field(default=None, max_length=100)
    sort_order: int | None = None
    product_group: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=100)
    unit_barcode: str | None = Field(default=None, max_length=50)
    box_barcode: str | None = Field(default=None, max_length=50)
    unit_volume: str | None = Field(default=None, max_length=50)
    net_weight: str | None = Field(default=None, max_length=50)
    pieces_per_box: int | None = None
    shelf_life: str | None = Field(default=None, max_length=100)
    nutrition_facts: str | None = None
    is_active: bool | None = None


class ProductDistributorsRequest(BaseModel):
    distributor_ids: list[uuid.UUID] = Field(default_factory=list)


@router.get("")
@router.get("/")
async def list_products(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=100),
    product_group: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProductsService(db)
    if auth.user.role.value == "admin" and include_inactive:
        data = await service.list_products_admin(
            page=page,
            limit=limit,
            include_inactive=True,
            product_group=product_group,
        )
    else:
        data = await service.list_products(
            user=auth.user,
            page=page,
            limit=limit,
            product_group=product_group,
        )
    return {"success": True, "data": data}


@router.get("/groups")
async def list_product_groups(
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProductsService(db)
    groups = await service.list_groups(user=auth.user)
    return {"success": True, "data": {"groups": groups}}


@router.post("/")
async def create_product(
    payload: ProductCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProductsService(db)
    try:
        data = await service.create_product(
            admin=auth.user,
            article=payload.article,
            name=payload.name,
            description=payload.description,
            image_url=payload.image_url,
            category=payload.category,
            product_kind=payload.product_kind,
            flavor=payload.flavor,
            composition=payload.composition,
            weight_volume=payload.weight_volume,
            sort_order=payload.sort_order,
            product_group=payload.product_group,
            brand=payload.brand,
            code=payload.code,
            unit_barcode=payload.unit_barcode,
            box_barcode=payload.box_barcode,
            unit_volume=payload.unit_volume,
            net_weight=payload.net_weight,
            pieces_per_box=payload.pieces_per_box,
            shelf_life=payload.shelf_life,
            nutrition_facts=payload.nutrition_facts,
            distributor_ids=payload.distributor_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.get("/{product_id}")
async def get_product(
    product_id: uuid.UUID,
    auth: AuthContext = Depends(require_registration_complete),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProductsService(db)
    try:
        data = await service.get_product(user=auth.user, product_id=product_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.put("/{product_id}")
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProductsService(db)
    try:
        data = await service.update_product(
            admin=auth.user,
            product_id=product_id,
            updates=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.delete("/{product_id}")
async def hide_product(
    product_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProductsService(db)
    try:
        data = await service.hide_product(admin=auth.user, product_id=product_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.put("/{product_id}/distributors")
async def set_product_distributors(
    product_id: uuid.UUID,
    payload: ProductDistributorsRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ProductsService(db)
    try:
        data = await service.set_product_distributors(
            admin=auth.user,
            product_id=product_id,
            distributor_ids=payload.distributor_ids,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": data}
