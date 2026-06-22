import json
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from bs4 import BeautifulSoup, Tag
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProductSource, SystemLogLevel
from app.models.parser_config import ParserConfig
from app.models.product import Product
from app.models.system_log import SystemLog
from app.models.user import User
from app.services.users import write_admin_log

DONOR_DEFAULT_URL = "https://omoloko.ru/catalog/icecream"
DEFAULT_MAX_PRODUCTS = 200
PARSER_SOURCE = "parser"
PARSER_FIELDS = {
    "article",
    "name",
    "description",
    "image_url",
    "category",
    "product_kind",
    "flavor",
    "composition",
    "weight_volume",
    "sort_order",
    "product_group",
    "brand",
    "code",
    "unit_barcode",
    "box_barcode",
    "unit_volume",
    "net_weight",
    "pieces_per_box",
}

DEFAULT_SELECTORS_CONFIG: dict[str, Any] = {
    "product_card_selectors": [
        ".catalog-grid .catalog-item",
        ".catalog-item",
        ".product-card",
        "article",
        "li",
    ],
    "field_selectors": {
        "article": [
            "[data-article]",
            "[data-code]",
            ".product-card__article",
            ".article",
            ".catalog-item__article",
        ],
        "name": [
            ".catalog-item__title",
            ".product-card__title",
            ".title",
            "h3",
            "h2",
        ],
        "description": [
            ".catalog-item__description",
            ".product-card__description",
            ".description",
            "p",
        ],
        "image_url": [
            "img",
            ".catalog-item__image img",
            ".product-card__image img",
        ],
        "category": [".category", ".catalog-item__category", ".product-card__category"],
        "product_kind": [".kind", ".type", ".catalog-item__type"],
        "flavor": [".flavor", ".taste"],
        "composition": [".composition", ".ingredients"],
        "weight_volume": [".weight", ".volume", ".weight-volume"],
        "product_group": [".group", ".catalog-item__group"],
        "brand": [".brand"],
        "code": [".code"],
        "unit_barcode": [".barcode-unit", ".unit-barcode"],
        "box_barcode": [".barcode-box", ".box-barcode"],
        "unit_volume": [".unit-volume"],
        "net_weight": [".net-weight"],
        "pieces_per_box": [".pieces-per-box"],
    },
    "image_attr_candidates": ["src", "data-src", "data-lazy", "srcset"],
}

CODE_RE = re.compile(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9_\-/]{1,99}")


@dataclass(slots=True)
class ParserRunStats:
    created: int = 0
    updated: int = 0
    skipped_existing: int = 0
    skipped_manual_override: int = 0
    skipped_invalid: int = 0


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _safe_json_loads(raw: str | None, fallback: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return fallback
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return fallback
    if isinstance(loaded, dict):
        return loaded
    return fallback


def _extract_text(card: Tag, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = card.select_one(selector)
        if node is None:
            continue
        text = _normalize_text(node.get_text(" ", strip=True))
        if text:
            return text
    return None


def _extract_image(card: Tag, selectors: list[str], attrs: list[str], base_url: str) -> str | None:
    for selector in selectors:
        node = card.select_one(selector)
        if node is None:
            continue
        for attr in attrs:
            value = _normalize_text(node.get(attr))
            if not value:
                continue
            if attr == "srcset":
                value = value.split(",")[0].strip().split(" ")[0]
            return urljoin(base_url, value)
    return None


def _extract_article(card: Tag, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = card.select_one(selector)
        if node is None:
            continue
        for attr in ("data-article", "data-code", "content"):
            raw = _normalize_text(node.get(attr))
            if raw:
                match = CODE_RE.search(raw)
                if match:
                    return match.group(0)
        text = _normalize_text(node.get_text(" ", strip=True))
        if text:
            match = CODE_RE.search(text)
            if match:
                return match.group(0)

    for attr in ("data-article", "data-code"):
        raw = _normalize_text(card.get(attr))
        if raw:
            match = CODE_RE.search(raw)
            if match:
                return match.group(0)

    link = card.select_one("a[href]")
    if link is not None:
        href = _normalize_text(link.get("href"))
        if href:
            match = CODE_RE.search(href.replace("/", "-"))
            if match:
                return match.group(0)
    return None


def _extract_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.findall(r"\d+", value)
    if not digits:
        return None
    try:
        return int(digits[0])
    except ValueError:
        return None


def _select_cards(soup: BeautifulSoup, selectors: list[str]) -> list[Tag]:
    for selector in selectors:
        cards = [item for item in soup.select(selector) if isinstance(item, Tag)]
        if len(cards) >= 3:
            return cards
    return [item for item in soup.select("article, .catalog-item, .product-card") if isinstance(item, Tag)]


class ParserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_config(self) -> dict[str, Any]:
        config = await self._get_or_create_config()
        return self._serialize_config(config)

    async def update_config(
        self,
        *,
        admin: User,
        source_url: str | None,
        selectors_config: dict[str, Any] | None,
        is_active: bool | None,
    ) -> dict[str, Any]:
        config = await self._get_or_create_config()
        old_value = self._serialize_config(config)

        if source_url is not None:
            normalized_url = source_url.strip()
            if not normalized_url.startswith(("http://", "https://")):
                raise ValueError("source_url должен начинаться с http:// или https://")
            config.source_url = normalized_url

        if selectors_config is not None:
            if not isinstance(selectors_config, dict):
                raise ValueError("selectors_config должен быть JSON-объектом")
            config.selectors_config = json.dumps(selectors_config, ensure_ascii=False)

        if is_active is not None:
            config.is_active = is_active

        config.updated_by = admin.id
        await write_admin_log(
            self.db,
            admin=admin,
            action="update_parser_config",
            entity_type="parser_config",
            entity_id=config.id,
            old_value=old_value,
            new_value=self._serialize_config(config),
        )
        await self.db.commit()
        await self.db.refresh(config)
        return self._serialize_config(config)

    async def run_parser(
        self,
        *,
        admin: User,
        update_existing: bool,
        fields_to_update: list[str] | None,
        max_products: int,
    ) -> dict[str, Any]:
        config = await self._get_or_create_config()
        if not config.is_active:
            raise ValueError("Парсер выключен в конфигурации")

        target_fields = self._normalize_fields(fields_to_update)
        selectors = _safe_json_loads(config.selectors_config, DEFAULT_SELECTORS_CONFIG)
        parsed_items = await self._fetch_products(
            source_url=config.source_url,
            selectors_config=selectors,
            max_products=max_products,
        )

        by_article: dict[str, dict[str, Any]] = {}
        for item in parsed_items:
            article = item.get("article")
            name = item.get("name")
            if not article or not name:
                continue
            by_article[article] = item

        existing = (
            await self.db.scalars(select(Product).where(Product.article.in_(list(by_article.keys()))))
        ).all()
        existing_by_article = {item.article: item for item in existing}

        stats = ParserRunStats()
        for article, payload in by_article.items():
            product = existing_by_article.get(article)
            if product is None:
                self.db.add(self._build_product(payload))
                stats.created += 1
                continue

            if not update_existing:
                stats.skipped_existing += 1
                continue

            updated = self._update_existing_product(product, payload, target_fields)
            if updated:
                stats.updated += 1
            else:
                stats.skipped_manual_override += 1

        result = {
            "source_url": config.source_url,
            "parsed_count": len(parsed_items),
            "deduplicated_count": len(by_article),
            "created_count": stats.created,
            "updated_count": stats.updated,
            "skipped_existing_count": stats.skipped_existing,
            "skipped_manual_override_count": stats.skipped_manual_override,
            "fields_to_update": sorted(target_fields),
            "update_existing": update_existing,
        }

        config.updated_by = admin.id
        await write_admin_log(
            self.db,
            admin=admin,
            action="run_product_parser",
            entity_type="parser",
            new_value=result,
        )
        self.db.add(
            SystemLog(
                level=SystemLogLevel.INFO,
                source=PARSER_SOURCE,
                message="Ручной запуск парсера завершен",
                details=json.dumps(result, ensure_ascii=False),
            )
        )
        await self.db.commit()
        return result

    async def run_parser_scheduled(
        self,
        *,
        update_existing: bool = True,
        max_products: int = DEFAULT_MAX_PRODUCTS,
    ) -> dict[str, Any]:
        """Фоновый запуск парсера без ручного действия администратора."""
        config = await self._get_or_create_config()
        if not config.is_active:
            return {"skipped": True, "reason": "parser_disabled"}

        target_fields = set(PARSER_FIELDS) - {"article"}
        selectors = _safe_json_loads(config.selectors_config, DEFAULT_SELECTORS_CONFIG)
        parsed_items = await self._fetch_products(
            source_url=config.source_url,
            selectors_config=selectors,
            max_products=max_products,
        )

        by_article: dict[str, dict[str, Any]] = {}
        for item in parsed_items:
            article = item.get("article")
            name = item.get("name")
            if not article or not name:
                continue
            by_article[article] = item

        existing = (
            await self.db.scalars(select(Product).where(Product.article.in_(list(by_article.keys()))))
        ).all()
        existing_by_article = {item.article: item for item in existing}

        stats = ParserRunStats()
        for article, payload in by_article.items():
            product = existing_by_article.get(article)
            if product is None:
                self.db.add(self._build_product(payload))
                stats.created += 1
                continue

            if not update_existing:
                stats.skipped_existing += 1
                continue

            updated = self._update_existing_product(product, payload, target_fields)
            if updated:
                stats.updated += 1
            else:
                stats.skipped_manual_override += 1

        result = {
            "source_url": config.source_url,
            "parsed_count": len(parsed_items),
            "deduplicated_count": len(by_article),
            "created_count": stats.created,
            "updated_count": stats.updated,
            "skipped_existing_count": stats.skipped_existing,
            "skipped_manual_override_count": stats.skipped_manual_override,
            "scheduled": True,
        }

        self.db.add(
            SystemLog(
                level=SystemLogLevel.INFO,
                source=PARSER_SOURCE,
                message="Плановый запуск парсера завершен",
                details=json.dumps(result, ensure_ascii=False),
            )
        )
        await self.db.commit()
        return result

    async def get_logs(self, *, page: int, limit: int) -> dict[str, Any]:
        normalized_page = max(page, 1)
        normalized_limit = min(max(limit, 1), 100)
        query = (
            select(SystemLog)
            .where(SystemLog.source == PARSER_SOURCE)
            .order_by(desc(SystemLog.created_at))
            .offset((normalized_page - 1) * normalized_limit)
            .limit(normalized_limit)
        )
        rows = (await self.db.scalars(query)).all()
        items: list[dict[str, Any]] = []
        for row in rows:
            parsed_details = None
            if row.details:
                try:
                    parsed_details = json.loads(row.details)
                except json.JSONDecodeError:
                    parsed_details = row.details
            items.append(
                {
                    "id": str(row.id),
                    "level": row.level.value,
                    "message": row.message,
                    "details": parsed_details,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return {
            "items": items,
            "pagination": {"current_page": normalized_page, "limit": normalized_limit},
        }

    async def _get_or_create_config(self) -> ParserConfig:
        config = await self.db.scalar(select(ParserConfig).limit(1))
        if config is not None:
            return config

        config = ParserConfig(
            source_url=DONOR_DEFAULT_URL,
            selectors_config=json.dumps(DEFAULT_SELECTORS_CONFIG, ensure_ascii=False),
            is_active=True,
            updated_by=None,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    def _serialize_config(self, config: ParserConfig) -> dict[str, Any]:
        return {
            "id": str(config.id),
            "source_url": config.source_url,
            "selectors_config": _safe_json_loads(config.selectors_config, DEFAULT_SELECTORS_CONFIG),
            "is_active": config.is_active,
            "updated_by": str(config.updated_by) if config.updated_by else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            "available_fields": sorted(PARSER_FIELDS),
        }

    def _normalize_fields(self, fields_to_update: list[str] | None) -> set[str]:
        if not fields_to_update:
            return set(PARSER_FIELDS)
        unknown_fields = [item for item in fields_to_update if item not in PARSER_FIELDS]
        if unknown_fields:
            raise ValueError(f"Неизвестные поля: {', '.join(sorted(unknown_fields))}")
        return set(fields_to_update)

    async def _fetch_products(
        self,
        *,
        source_url: str,
        selectors_config: dict[str, Any],
        max_products: int,
    ) -> list[dict[str, Any]]:
        try:
            return await self._fetch_products_inner(
                source_url=source_url,
                selectors_config=selectors_config,
                max_products=max_products,
            )
        except Exception as exc:
            details = {"source_url": source_url, "error": str(exc)}
            self.db.add(
                SystemLog(
                    level=SystemLogLevel.ERROR,
                    source=PARSER_SOURCE,
                    message="Ошибка запуска парсера omoloko.ru",
                    details=json.dumps(details, ensure_ascii=False),
                )
            )
            await self.db.commit()
            raise RuntimeError("Парсер не смог получить данные с сайта-донора") from exc

    async def _fetch_products_inner(
        self,
        *,
        source_url: str,
        selectors_config: dict[str, Any],
        max_products: int,
    ) -> list[dict[str, Any]]:
        html = await self._download_html(source_url)
        soup = BeautifulSoup(html, "html.parser")

        card_selectors_raw = selectors_config.get("product_card_selectors", [])
        field_selectors_raw = selectors_config.get("field_selectors", {})
        attrs_raw = selectors_config.get("image_attr_candidates", [])
        card_selectors = [item for item in card_selectors_raw if isinstance(item, str)]
        image_attrs = [item for item in attrs_raw if isinstance(item, str)] or ["src"]
        field_selectors = (
            field_selectors_raw if isinstance(field_selectors_raw, dict) else DEFAULT_SELECTORS_CONFIG["field_selectors"]
        )

        cards = _select_cards(soup, card_selectors)
        payloads: list[dict[str, Any]] = []
        for index, card in enumerate(cards[:max_products]):
            field = lambda key: [item for item in field_selectors.get(key, []) if isinstance(item, str)]
            article = _extract_article(card, field("article"))
            name = _extract_text(card, field("name"))
            if not article and name:
                article = f"AUTO-{uuid.uuid5(uuid.NAMESPACE_URL, name + str(index)).hex[:12]}"
            payloads.append(
                {
                    "article": article,
                    "name": name,
                    "description": _extract_text(card, field("description")),
                    "image_url": _extract_image(card, field("image_url"), image_attrs, source_url),
                    "category": _extract_text(card, field("category")),
                    "product_kind": _extract_text(card, field("product_kind")),
                    "flavor": _extract_text(card, field("flavor")),
                    "composition": _extract_text(card, field("composition")),
                    "weight_volume": _extract_text(card, field("weight_volume")),
                    "product_group": _extract_text(card, field("product_group")),
                    "brand": _extract_text(card, field("brand")),
                    "code": _extract_text(card, field("code")),
                    "unit_barcode": _extract_text(card, field("unit_barcode")),
                    "box_barcode": _extract_text(card, field("box_barcode")),
                    "unit_volume": _extract_text(card, field("unit_volume")),
                    "net_weight": _extract_text(card, field("net_weight")),
                    "pieces_per_box": _extract_int(_extract_text(card, field("pieces_per_box"))),
                    "sort_order": index,
                }
            )
        return payloads

    async def _download_html(self, source_url: str) -> str:
        def _load() -> str:
            request = UrlRequest(
                source_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
            with urlopen(request, timeout=20) as response:  # noqa: S310
                data = response.read()
            return data.decode("utf-8", errors="ignore")

        import asyncio

        return await asyncio.to_thread(_load)

    def _build_product(self, payload: dict[str, Any]) -> Product:
        return Product(
            article=payload["article"],
            name=payload["name"],
            description=payload.get("description"),
            image_url=payload.get("image_url"),
            category=payload.get("category"),
            product_kind=payload.get("product_kind"),
            flavor=payload.get("flavor"),
            composition=payload.get("composition"),
            weight_volume=payload.get("weight_volume"),
            sort_order=payload.get("sort_order") or 0,
            product_group=payload.get("product_group"),
            brand=payload.get("brand"),
            code=payload.get("code"),
            unit_barcode=payload.get("unit_barcode"),
            box_barcode=payload.get("box_barcode"),
            unit_volume=payload.get("unit_volume"),
            net_weight=payload.get("net_weight"),
            pieces_per_box=payload.get("pieces_per_box"),
            source=ProductSource.parser,
            is_active=True,
        )

    def _update_existing_product(
        self,
        product: Product,
        payload: dict[str, Any],
        target_fields: set[str],
    ) -> bool:
        manual_overrides = product.manual_overrides or {}
        changed = False
        for field in target_fields:
            if field in {"article"}:
                continue
            if manual_overrides.get(field):
                continue
            new_value = payload.get(field)
            if getattr(product, field) != new_value:
                setattr(product, field, new_value)
                changed = True
        if changed:
            product.source = ProductSource.parser
        return changed
