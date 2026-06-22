import copy
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_setting import AdminSetting
from app.models.user import User
from app.services.users import write_admin_log

ALLOWED_CONTENT_SLUGS = frozenset({"faq", "instructions", "support_contacts"})

DEFAULT_CONTENT: dict[str, dict[str, Any]] = {
    "faq": {"items": []},
    "instructions": {
        "title": "Инструкция для участников",
        "content": "",
        "items": [],
    },
    "support_contacts": {
        "phone": "",
        "email": "",
        "work_hours": "",
        "text": "",
    },
}


def _deep_copy_default(slug: str) -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_CONTENT[slug])


def _normalize_faq_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not question and not answer:
            continue

        item_id = str(item.get("id") or uuid.uuid4())
        normalized.append(
            {
                "id": item_id,
                "question": question,
                "answer": answer,
                "sort_order": int(item.get("sort_order", index)),
                "is_published": bool(item.get("is_published", True)),
            }
        )
    normalized.sort(key=lambda entry: entry["sort_order"])
    return normalized


def _normalize_instruction_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        file_path = str(item.get("file_path", "")).strip() or None
        if not title and not description and not file_path:
            continue

        item_id = str(item.get("id") or uuid.uuid4())
        normalized.append(
            {
                "id": item_id,
                "title": title,
                "description": description,
                "file_path": file_path,
                "sort_order": int(item.get("sort_order", index)),
                "is_published": bool(item.get("is_published", True)),
            }
        )
    normalized.sort(key=lambda entry: entry["sort_order"])
    return normalized


def _normalize_support_contacts(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "phone": str(value.get("phone", "")).strip(),
        "email": str(value.get("email", "")).strip(),
        "work_hours": str(value.get("work_hours", "")).strip(),
        "text": str(value.get("text", "")).strip(),
    }


def _validate_and_normalize_content(slug: str, value: dict[str, Any]) -> dict[str, Any]:
    if slug == "faq":
        items = value.get("items", [])
        if not isinstance(items, list):
            raise ValueError("FAQ должен содержать список вопросов")
        return {"items": _normalize_faq_items(items)}

    if slug == "instructions":
        items = value.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Инструкции должны содержать список материалов")
        return {
            "title": str(value.get("title", DEFAULT_CONTENT["instructions"]["title"])).strip()
            or DEFAULT_CONTENT["instructions"]["title"],
            "content": str(value.get("content", "")).strip(),
            "items": _normalize_instruction_items(items),
        }

    if slug == "support_contacts":
        return _normalize_support_contacts(value)

    raise ValueError("Неизвестный раздел контента")


def _filter_for_user(slug: str, value: dict[str, Any]) -> dict[str, Any]:
    if slug == "faq":
        return {
            "items": [
                item
                for item in value.get("items", [])
                if item.get("is_published", True)
            ]
        }

    if slug == "instructions":
        return {
            "title": value.get("title", DEFAULT_CONTENT["instructions"]["title"]),
            "content": value.get("content", ""),
            "items": [
                item
                for item in value.get("items", [])
                if item.get("is_published", True)
            ],
        }

    return value


class ContentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_content(self, *, slug: str, user: User) -> dict[str, Any]:
        self._validate_slug(slug)
        stored = await self._get_setting(slug)
        value = stored.setting_value if stored else _deep_copy_default(slug)
        is_admin = user.role.value == "admin"
        payload = value if is_admin else _filter_for_user(slug, value)

        return {
            "slug": slug,
            "value": payload,
            "updated_at": stored.updated_at.isoformat() if stored and stored.updated_at else None,
        }

    async def update_content(
        self,
        *,
        slug: str,
        admin: User,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_slug(slug)
        normalized_value = _validate_and_normalize_content(slug, value)
        stored = await self._get_setting(slug)
        old_value = stored.setting_value if stored else _deep_copy_default(slug)

        if stored is None:
            stored = AdminSetting(
                admin_id=admin.id,
                setting_key=slug,
                setting_value=normalized_value,
            )
            self.db.add(stored)
        else:
            stored.admin_id = admin.id
            stored.setting_value = normalized_value

        await write_admin_log(
            self.db,
            admin=admin,
            action="update_content",
            entity_type="content",
            entity_id=stored.id,
            old_value={"slug": slug, "value": old_value},
            new_value={"slug": slug, "value": normalized_value},
        )
        await self.db.commit()
        await self.db.refresh(stored)

        return {
            "slug": slug,
            "value": normalized_value,
            "updated_at": stored.updated_at.isoformat() if stored.updated_at else None,
        }

    async def _get_setting(self, slug: str) -> AdminSetting | None:
        return await self.db.scalar(
            select(AdminSetting)
            .where(AdminSetting.setting_key == slug)
            .order_by(AdminSetting.updated_at.desc())
            .limit(1)
        )

    def _validate_slug(self, slug: str) -> None:
        if slug not in ALLOWED_CONTENT_SLUGS:
            raise ValueError("Неизвестный раздел контента")
