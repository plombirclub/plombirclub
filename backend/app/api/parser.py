from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext, require_admin
from app.core.database import get_db_session
from app.services.parser import DEFAULT_MAX_PRODUCTS, ParserService

router = APIRouter(prefix="/parser", tags=["parser"])


class ParserConfigUpdateRequest(BaseModel):
    source_url: str | None = None
    selectors_config: dict[str, Any] | None = None
    is_active: bool | None = None


class ParserRunRequest(BaseModel):
    update_existing: bool = False
    fields_to_update: list[str] | None = None
    max_products: int = Field(default=DEFAULT_MAX_PRODUCTS, ge=1, le=500)


@router.get("/config")
async def get_parser_config(
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ParserService(db)
    return {"success": True, "data": await service.get_config()}


@router.put("/config")
async def update_parser_config(
    payload: ParserConfigUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if (
        payload.source_url is None
        and payload.selectors_config is None
        and payload.is_active is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Передайте хотя бы одно поле: source_url, selectors_config или is_active",
        )

    service = ParserService(db)
    try:
        data = await service.update_config(
            admin=auth.user,
            source_url=payload.source_url,
            selectors_config=payload.selectors_config,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "data": data}


@router.post("/run")
async def run_parser(
    payload: ParserRunRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ParserService(db)
    try:
        data = await service.run_parser(
            admin=auth.user,
            update_existing=payload.update_existing,
            fields_to_update=payload.fields_to_update,
            max_products=payload.max_products,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {"success": True, "data": data}


@router.get("/logs")
async def get_parser_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ParserService(db)
    data = await service.get_logs(page=page, limit=limit)
    return {"success": True, "data": data}
