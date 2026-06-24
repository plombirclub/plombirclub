import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse
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
    "shelf_life",
    "nutrition_facts",
}

FIELD_MAX_LENGTHS: dict[str, int] = {
    "article": 100,
    "name": 255,
    "image_url": 500,
    "category": 255,
    "product_kind": 255,
    "flavor": 255,
    "weight_volume": 100,
    "product_group": 255,
    "brand": 255,
    "code": 100,
    "unit_barcode": 50,
    "box_barcode": 50,
    "unit_volume": 50,
    "net_weight": 50,
    "shelf_life": 100,
}

DEFAULT_SELECTORS_CONFIG: dict[str, Any] = {
    "parser_mode": "omoloko",
    "product_link_pattern": r"/catalog/icecream/[^/]+/[^/?#]+",
    "article_pattern": r"Артикул:\s*(\d+)",
    "category_map": {
        "eskimo": "Эскимо",
        "trays": "Лотки",
        "cups": "Стаканчики",
        "sandwiches": "Сэндвичи и батончики",
        "cones": "Рожки",
        "lakomka": "Московская лакомка",
        "tubi": "Тубы",
        "bucket": "Ведёрки",
        "familypacks": "Семейные упаковки",
        "cartons": "Брикеты",
    },
}

OMOLOKO_PRODUCT_LINK_RE = re.compile(r"/catalog/icecream/[^/]+/[^/?#]+", re.IGNORECASE)
OMOLOKO_ARTICLE_RE = re.compile(r"Артикул:\s*(\d+)", re.IGNORECASE)
WEIGHT_RE = re.compile(r"(\d+(?:[.,]\d+)?\s*(?:г|кг|мл|л))\s*$", re.IGNORECASE)
PRICE_RE = re.compile(r"^\d[\d\s.,]*₽")
OMOLOKO_PRODUCT_IMAGE_RE = re.compile(
    r"(?:storage\.omoloko\.ru/.*/products|/img/products/)",
    re.IGNORECASE,
)
OMOLOKO_DETAIL_STOP_RE = re.compile(
    r"(Рекомендуем попробовать|Похожие товары|Отзывы)",
    re.IGNORECASE,
)
PARSER_CLEARABLE_FIELDS = set(PARSER_FIELDS) - {"article", "name", "sort_order"}


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


def _clip_text(value: str | None, max_len: int) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized[:max_len]


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


def _sanitize_image_url(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    if normalized.startswith(("http://", "https://")):
        return _clip_text(normalized, FIELD_MAX_LENGTHS["image_url"])
    return None


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    for field, max_len in FIELD_MAX_LENGTHS.items():
        if field in sanitized and isinstance(sanitized[field], str):
            sanitized[field] = _clip_text(sanitized[field], max_len)
    sanitized["image_url"] = _sanitize_image_url(sanitized.get("image_url"))
    if sanitized.get("description"):
        sanitized["description"] = _normalize_text(str(sanitized["description"]))
    return sanitized


def _normalize_href(href: str | None, base_url: str) -> str | None:
    if not href:
        return None
    return urljoin(base_url, href.split("?")[0].split("#")[0])


def _product_path_key(href: str) -> str | None:
    parsed = urlparse(href)
    path = parsed.path.rstrip("/")
    if not OMOLOKO_PRODUCT_LINK_RE.search(path):
        return None
    return path.lower()


def _category_from_path(path: str, category_map: dict[str, str]) -> str | None:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 4:
        return None
    slug = parts[2].lower()
    return category_map.get(slug) or slug.replace("-", " ").capitalize()


def _find_product_card(anchor: Tag) -> Tag:
    node: Tag | None = anchor
    for _ in range(10):
        if node is None or node.parent is None:
            break
        node = node.parent
        text = node.get_text(" ", strip=True)
        if OMOLOKO_ARTICLE_RE.search(text):
            return node
    return anchor.parent if anchor.parent is not None else anchor


def _extract_omoloko_image(card: Tag, base_url: str) -> str | None:
    for img in card.select("img"):
        for attr in ("src", "data-src", "data-original", "data-lazy"):
            raw = _normalize_text(img.get(attr))
            if raw:
                resolved = urljoin(base_url, raw)
                sanitized = _sanitize_image_url(resolved)
                if sanitized:
                    return sanitized
    return None


def _extract_omoloko_name(card: Tag, article: str, product_href: str) -> str | None:
    for anchor in card.select("a[href]"):
        href = _normalize_href(anchor.get("href"), product_href)
        if href and _product_path_key(href) == _product_path_key(product_href):
            text = _normalize_text(anchor.get_text(" ", strip=True))
            if text and not text.startswith("http") and "Артикул" not in text and "₽" not in text:
                return text

    lines = [line.strip() for line in card.get_text("\n", strip=True).split("\n") if line.strip()]
    for index, line in enumerate(lines):
        if line == f"Артикул: {article}" or line.endswith(f"Артикул: {article}"):
            for candidate in lines[index + 1 : index + 5]:
                if candidate.startswith("http") or "Артикул" in candidate or PRICE_RE.search(candidate):
                    continue
                if candidate.lower() in {"в корзину", "нет на складе"}:
                    continue
                normalized = _normalize_text(candidate)
                if normalized and len(normalized) > 3:
                    return normalized

    for selector in ("h2", "h3", "h4", '[class*="title"]', '[class*="name"]'):
        node = card.select_one(selector)
        if node is None:
            continue
        text = _normalize_text(node.get_text(" ", strip=True))
        if text and "Артикул" not in text and "₽" not in text:
            return text
    return None


def _split_name_and_description(name: str | None) -> tuple[str | None, str | None]:
    normalized = _normalize_text(name)
    if not normalized:
        return None, None

    weight_match = WEIGHT_RE.search(normalized)
    if weight_match:
        cut_at = weight_match.end()
        short_name = _normalize_text(normalized[:cut_at])
        tail = _normalize_text(normalized[cut_at:])
        if short_name and len(short_name) <= FIELD_MAX_LENGTHS["name"]:
            return short_name, tail
    if len(normalized) <= FIELD_MAX_LENGTHS["name"]:
        return normalized, None
    clipped = _clip_text(normalized, FIELD_MAX_LENGTHS["name"])
    description = _normalize_text(normalized[len(clipped or "") :])
    return clipped, description


def _extract_weight_volume(name: str | None) -> str | None:
    normalized = _normalize_text(name)
    if not normalized:
        return None
    match = WEIGHT_RE.search(normalized)
    if match:
        return _clip_text(match.group(1), FIELD_MAX_LENGTHS["weight_volume"])
    return None


def _extract_omoloko_product_image(soup: BeautifulSoup, source_url: str) -> str | None:
    for img in soup.select("img"):
        for attr in ("src", "data-src", "data-lazy", "data-original", "data-zoom-image"):
            raw = _normalize_text(img.get(attr))
            if not raw:
                continue
            resolved = urljoin(source_url, raw)
            if not OMOLOKO_PRODUCT_IMAGE_RE.search(resolved):
                continue
            sanitized = _sanitize_image_url(resolved)
            if sanitized:
                return sanitized
    return None


def _extract_omoloko_product_details(html: str, product_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    plain_text = _normalize_text(soup.get_text(" ", strip=True)) or ""

    description = None
    description_match = re.search(
        r"(?:В корзину|без карты)\s*(.+?)\s*Доставка на следующий день",
        plain_text,
        re.IGNORECASE,
    )
    if description_match:
        description = _normalize_text(description_match.group(1))
        if description:
            description = re.sub(r"^в\s*корзину\s*", "", description, flags=re.IGNORECASE).strip()
            description = _normalize_text(description)

    composition = None
    pieces_per_box = None
    shelf_life = None
    nutrition_facts = None
    detail_match = re.search(r"О товаре\s*(.+)", plain_text, re.IGNORECASE)
    if detail_match:
        detail_text = OMOLOKO_DETAIL_STOP_RE.split(detail_match.group(1), maxsplit=1)[0]
        piece_match = re.search(r"Штук в коробке:\s*(\d+)", detail_text, re.IGNORECASE)
        if piece_match:
            pieces_per_box = int(piece_match.group(1))
        shelf_life_match = re.search(r"Срок годности:\s*([^:]+?)(?=Штук в коробке:|$)", detail_text, re.IGNORECASE)
        if shelf_life_match:
            shelf_life = _normalize_text(shelf_life_match.group(1))
        nutrition_match = re.search(
            r"В 100 граммах\s*(.+?)(?=Состав[^:]{0,120}:|Срок годности:|Штук в коробке:|$)",
            detail_text,
            re.IGNORECASE,
        )
        if nutrition_match:
            nutrition_facts = _normalize_text("В 100 граммах " + nutrition_match.group(1))
        compositions = re.findall(
            r"(Состав[^:]{0,120}:\s*.+?)(?=Состав[^:]{0,120}:|Срок годности:|Штук в коробке:|$)",
            detail_text,
            re.IGNORECASE,
        )
        if compositions:
            composition = "\n\n".join(
                _normalize_text(item) or "" for item in compositions if _normalize_text(item)
            ) or None
        else:
            composition = _normalize_text(detail_text)

    return _sanitize_payload(
        {
            "image_url": _extract_omoloko_product_image(soup, product_url),
            "description": description,
            "composition": composition,
            "pieces_per_box": pieces_per_box,
            "shelf_life": shelf_life,
            "nutrition_facts": nutrition_facts,
        }
    )


def _parse_omoloko_catalog(
    soup: BeautifulSoup,
    *,
    source_url: str,
    max_products: int,
    selectors_config: dict[str, Any],
) -> list[dict[str, Any]]:
    category_map_raw = selectors_config.get("category_map", {})
    category_map = (
        category_map_raw if isinstance(category_map_raw, dict) else DEFAULT_SELECTORS_CONFIG["category_map"]
    )

    by_path: dict[str, dict[str, Any]] = {}
    sort_order = 0

    for anchor in soup.select("a[href]"):
        href = _normalize_href(anchor.get("href"), source_url)
        if not href:
            continue
        path_key = _product_path_key(href)
        if not path_key or path_key in by_path:
            continue

        card = _find_product_card(anchor)
        card_text = card.get_text(" ", strip=True)
        article_match = OMOLOKO_ARTICLE_RE.search(card_text)
        if not article_match:
            continue

        article = article_match.group(1)
        raw_name = _extract_omoloko_name(card, article, href)
        if not raw_name:
            continue

        name, extra_description = _split_name_and_description(raw_name)
        if not name:
            continue

        by_path[path_key] = _sanitize_payload(
            {
                "article": article,
                "name": name,
                "description": extra_description,
                "image_url": _extract_omoloko_image(card, source_url),
                "category": "Мороженое",
                "product_group": _category_from_path(path_key, category_map),
                "weight_volume": _extract_weight_volume(raw_name),
                "brand": "Чистая Линия",
                "code": article,
                "sort_order": sort_order,
                "source_path": path_key,
                "product_url": href,
            }
        )
        sort_order += 1
        if len(by_path) >= max_products:
            break

    return list(by_path.values())


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

        result = await self._persist_products(
            parsed_items=parsed_items,
            source_url=config.source_url,
            update_existing=update_existing,
            target_fields=target_fields,
        )

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

        result = await self._persist_products(
            parsed_items=parsed_items,
            source_url=config.source_url,
            update_existing=update_existing,
            target_fields=target_fields,
        )
        result["scheduled"] = True

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

    async def _persist_products(
        self,
        *,
        parsed_items: list[dict[str, Any]],
        source_url: str,
        update_existing: bool,
        target_fields: set[str],
    ) -> dict[str, Any]:
        by_article: dict[str, dict[str, Any]] = {}
        for item in parsed_items:
            article = item.get("article")
            name = item.get("name")
            if not article or not name:
                continue
            by_article[str(article)] = _sanitize_payload(item)

        existing_by_article: dict[str, Product] = {}
        if by_article:
            existing = (
                await self.db.scalars(
                    select(Product).where(Product.article.in_(list(by_article.keys())))
                )
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

        return {
            "source_url": source_url,
            "parsed_count": len(parsed_items),
            "deduplicated_count": len(by_article),
            "created_count": stats.created,
            "updated_count": stats.updated,
            "skipped_existing_count": stats.skipped_existing,
            "skipped_manual_override_count": stats.skipped_manual_override,
            "fields_to_update": sorted(target_fields),
            "update_existing": update_existing,
        }

    async def _get_or_create_config(self) -> ParserConfig:
        config = await self.db.scalar(select(ParserConfig).limit(1))
        if config is not None:
            if "omoloko.ru" in config.source_url and _safe_json_loads(
                config.selectors_config, {}
            ).get("parser_mode") != "omoloko":
                config.selectors_config = json.dumps(DEFAULT_SELECTORS_CONFIG, ensure_ascii=False)
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
        if fields_to_update is None:
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

        if "omoloko.ru" in source_url:
            items = _parse_omoloko_catalog(
                soup,
                source_url=source_url,
                max_products=max_products,
                selectors_config=selectors_config,
            )
            if items:
                await self._enrich_omoloko_items(items)
                return items

        raise RuntimeError("На странице omoloko.ru не найдено карточек товаров")

    async def _enrich_omoloko_items(self, items: list[dict[str, Any]]) -> None:
        semaphore = asyncio.Semaphore(6)

        async def enrich(item: dict[str, Any]) -> None:
            product_url = _normalize_text(item.get("product_url"))
            if not product_url:
                return
            async with semaphore:
                try:
                    html = await self._download_html(product_url)
                    details = _extract_omoloko_product_details(html, product_url)
                except Exception:
                    return
            for field in (
                "image_url",
                "description",
                "composition",
                "pieces_per_box",
                "shelf_life",
                "nutrition_facts",
            ):
                value = details.get(field)
                if value in (None, ""):
                    continue
                item[field] = value

        await asyncio.gather(*(enrich(item) for item in items))

    async def _download_html(self, source_url: str) -> str:
        def _load() -> str:
            request = UrlRequest(
                source_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "ru-RU,ru;q=0.9",
                },
            )
            with urlopen(request, timeout=30) as response:  # noqa: S310
                data = response.read()
            return data.decode("utf-8", errors="ignore")

        return await asyncio.to_thread(_load)

    def _build_product(self, payload: dict[str, Any]) -> Product:
        sanitized = _sanitize_payload(payload)
        return Product(
            article=sanitized["article"],
            name=sanitized["name"],
            description=sanitized.get("description"),
            image_url=sanitized.get("image_url"),
            category=sanitized.get("category"),
            product_kind=sanitized.get("product_kind"),
            flavor=sanitized.get("flavor"),
            composition=sanitized.get("composition"),
            weight_volume=sanitized.get("weight_volume"),
            sort_order=sanitized.get("sort_order") or 0,
            product_group=sanitized.get("product_group"),
            brand=sanitized.get("brand"),
            code=sanitized.get("code"),
            unit_barcode=sanitized.get("unit_barcode"),
            box_barcode=sanitized.get("box_barcode"),
            unit_volume=sanitized.get("unit_volume"),
            net_weight=sanitized.get("net_weight"),
            pieces_per_box=sanitized.get("pieces_per_box"),
            shelf_life=sanitized.get("shelf_life"),
            nutrition_facts=sanitized.get("nutrition_facts"),
            source=ProductSource.parser,
            is_active=True,
        )

    def _update_existing_product(
        self,
        product: Product,
        payload: dict[str, Any],
        target_fields: set[str],
    ) -> bool:
        sanitized = _sanitize_payload(payload)
        manual_overrides = product.manual_overrides or {}
        changed = False
        for field in target_fields:
            if field in {"article"}:
                continue
            if manual_overrides.get(field):
                continue
            new_value = sanitized.get(field)
            if getattr(product, field) != new_value:
                setattr(product, field, new_value)
                changed = True

        for field in sorted(PARSER_CLEARABLE_FIELDS - target_fields):
            if manual_overrides.get(field):
                continue
            current_value = getattr(product, field)
            if current_value is not None:
                setattr(product, field, None)
                changed = True
        if changed:
            product.source = ProductSource.parser
        return changed
