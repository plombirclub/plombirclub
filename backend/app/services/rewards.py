import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.distributor import Distributor
from app.models.enums import PrizeType
from app.models.prize import Prize
from app.models.prize_distributor import PrizeDistributor
from app.models.user import User
from app.services.users import write_admin_log


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _uploads_url(path: str | None) -> str | None:
    if not path:
        return None
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized.startswith("uploads/"):
        return f"/{normalized}"
    return f"/uploads/{normalized}"


def _serialize_reward(prize: Prize) -> dict[str, Any]:
    file_url = _uploads_url(prize.image_file_path)
    link_url = prize.image_url
    display_image_url = file_url or link_url
    return {
        "id": str(prize.id),
        "name": prize.name,
        "description": prize.description,
        "type": prize.type.value,
        "is_system": prize.is_system,
        "is_active": prize.is_active,
        "image_url": link_url,
        "image_file_path": prize.image_file_path,
        "image_file_url": file_url,
        "display_image_url": display_image_url,
        "has_uploaded_image": bool(prize.image_file_path),
        "has_link": bool(link_url),
        "created_at": prize.created_at.isoformat() if prize.created_at else None,
        "updated_at": prize.updated_at.isoformat() if prize.updated_at else None,
    }


class RewardsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_rewards(
        self,
        *,
        page: int,
        limit: int,
        include_inactive: bool,
        is_admin: bool,
        user_distributor_id: uuid.UUID | None,
    ) -> dict[str, Any]:
        normalized_page = max(page, 1)
        normalized_limit = min(max(limit, 1), 100)
        show_inactive = include_inactive and is_admin

        base_query = select(Prize)
        count_query = select(func.count(Prize.id))
        if not show_inactive:
            base_query = base_query.where(Prize.is_active.is_(True))
            count_query = count_query.where(Prize.is_active.is_(True))

        total_count = int((await self.db.scalar(count_query)) or 0)
        total_pages = max((total_count + normalized_limit - 1) // normalized_limit, 1)
        if normalized_page > total_pages:
            normalized_page = total_pages

        items = (
            await self.db.scalars(
                base_query
                .order_by(Prize.is_system.desc(), Prize.created_at.desc())
                .offset((normalized_page - 1) * normalized_limit)
                .limit(normalized_limit)
            )
        ).all()

        mapped_items = [_serialize_reward(item) for item in items]

        if not is_admin:
            mapped_items = await self._filter_for_user(
                items=mapped_items,
                user_distributor_id=user_distributor_id,
            )

        return {
            "items": mapped_items,
            "pagination": {
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": normalized_page,
                "limit": normalized_limit,
            },
            "include_inactive": show_inactive,
        }

    async def create_reward(
        self,
        *,
        admin: User,
        name: str,
        description: str | None,
        prize_type: PrizeType,
        image_url: str | None,
        image_file_path: str | None = None,
        is_active: bool,
    ) -> dict[str, Any]:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название приза не может быть пустым")
        if prize_type != PrizeType.certificate:
            raise ValueError("Можно создавать только призы типа certificate")

        reward = Prize(
            name=normalized_name,
            description=_normalize_text(description),
            type=PrizeType.certificate,
            is_system=False,
            is_active=is_active,
            image_url=_normalize_text(image_url),
            image_file_path=_normalize_text(image_file_path),
        )
        self.db.add(reward)
        await self.db.flush()

        serialized = _serialize_reward(reward)
        await write_admin_log(
            self.db,
            admin=admin,
            action="create_reward",
            entity_type="prize",
            entity_id=reward.id,
            new_value=serialized,
        )
        await self.db.commit()
        await self.db.refresh(reward)
        return _serialize_reward(reward)

    async def update_reward(
        self,
        *,
        admin: User,
        reward_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        if not updates:
            raise ValueError("Нет полей для обновления")

        reward = await self.db.scalar(select(Prize).where(Prize.id == reward_id).limit(1))
        if reward is None:
            raise LookupError("Приз не найден")

        old_value = _serialize_reward(reward)

        if "name" in updates:
            normalized_name = updates["name"].strip()
            if not normalized_name:
                raise ValueError("Название приза не может быть пустым")
            reward.name = normalized_name

        if "description" in updates:
            reward.description = _normalize_text(updates["description"])

        if "image_url" in updates:
            reward.image_url = _normalize_text(updates["image_url"])

        if "image_file_path" in updates:
            reward.image_file_path = _normalize_text(updates["image_file_path"])

        if "type" in updates:
            new_type = updates["type"]
            if reward.is_system and new_type != reward.type:
                raise ValueError("Системному СБП-призу нельзя менять тип")
            if not reward.is_system and new_type != PrizeType.certificate:
                raise ValueError("Для обычных призов разрешен только тип certificate")
            reward.type = new_type

        if "is_active" in updates:
            if reward.is_system and updates["is_active"] is False:
                raise ValueError("Системный СБП-приз нельзя скрывать")
            reward.is_active = updates["is_active"]

        await write_admin_log(
            self.db,
            admin=admin,
            action="update_reward",
            entity_type="prize",
            entity_id=reward.id,
            old_value=old_value,
            new_value=_serialize_reward(reward),
        )
        await self.db.commit()
        await self.db.refresh(reward)
        return _serialize_reward(reward)

    async def hide_reward(
        self,
        *,
        admin: User,
        reward_id: uuid.UUID,
    ) -> dict[str, Any]:
        reward = await self.db.scalar(select(Prize).where(Prize.id == reward_id).limit(1))
        if reward is None:
            raise LookupError("Приз не найден")
        if reward.is_system:
            raise ValueError("Системный СБП-приз нельзя удалить или скрыть")

        old_value = _serialize_reward(reward)
        already_hidden = not reward.is_active
        reward.is_active = False

        await write_admin_log(
            self.db,
            admin=admin,
            action="hide_reward",
            entity_type="prize",
            entity_id=reward.id,
            old_value=old_value,
            new_value=_serialize_reward(reward),
        )
        await self.db.commit()
        await self.db.refresh(reward)
        return {
            **_serialize_reward(reward),
            "already_hidden": already_hidden,
        }

    async def set_reward_visibility(
        self,
        *,
        admin: User,
        reward_id: uuid.UUID,
        distributor_ids: list[uuid.UUID],
    ) -> dict[str, Any]:
        reward = await self.db.scalar(select(Prize).where(Prize.id == reward_id).limit(1))
        if reward is None:
            raise LookupError("Приз не найден")

        distributors = (
            await self.db.scalars(select(Distributor).where(Distributor.id.in_(distributor_ids)))
        ).all()
        found_ids = {item.id for item in distributors}
        missing_ids = [str(item) for item in distributor_ids if item not in found_ids]
        if missing_ids:
            raise LookupError(f"Дистрибьюторы не найдены: {', '.join(missing_ids)}")

        links = (
            await self.db.scalars(
                select(PrizeDistributor).where(PrizeDistributor.prize_id == reward_id)
            )
        ).all()
        links_by_distributor = {item.distributor_id: item for item in links}
        target_ids = set(distributor_ids)

        for distributor_id in target_ids:
            link = links_by_distributor.get(distributor_id)
            if link is None:
                self.db.add(
                    PrizeDistributor(
                        prize_id=reward_id,
                        distributor_id=distributor_id,
                        is_visible=True,
                    )
                )
                continue
            link.is_visible = True

        for link in links:
            if link.distributor_id not in target_ids:
                link.is_visible = False

        visible_names = [item.name for item in distributors]
        await write_admin_log(
            self.db,
            admin=admin,
            action="set_reward_visibility",
            entity_type="prize",
            entity_id=reward_id,
            new_value={
                "visible_distributor_ids": [str(item) for item in distributor_ids],
                "visible_distributor_names": visible_names,
            },
        )
        await self.db.commit()

        return {
            "reward_id": str(reward_id),
            "visible_distributor_ids": [str(item) for item in distributor_ids],
            "visible_distributor_names": visible_names,
        }

    async def set_system_reward_visibility(
        self,
        *,
        admin: User,
        reward_id: uuid.UUID,
        distributor_ids: list[uuid.UUID],
    ) -> dict[str, Any]:
        return await self.set_reward_visibility(
            admin=admin,
            reward_id=reward_id,
            distributor_ids=distributor_ids,
        )

    async def get_reward_visibility(
        self,
        *,
        reward_id: uuid.UUID,
    ) -> dict[str, Any]:
        reward = await self.db.scalar(select(Prize).where(Prize.id == reward_id).limit(1))
        if reward is None:
            raise LookupError("Приз не найден")

        links = (
            await self.db.scalars(
                select(PrizeDistributor).where(
                    PrizeDistributor.prize_id == reward_id,
                    PrizeDistributor.is_visible.is_(True),
                )
            )
        ).all()

        distributor_ids = [link.distributor_id for link in links]
        distributors = []
        if distributor_ids:
            distributors = (
                await self.db.scalars(select(Distributor).where(Distributor.id.in_(distributor_ids)))
            ).all()

        visible_links = [link for link in links if link.is_visible]
        return {
            "reward_id": str(reward_id),
            "is_system": reward.is_system,
            "type": reward.type.value,
            "visible_distributor_ids": [str(item.id) for item in distributors],
            "visible_distributor_names": [item.name for item in distributors],
            "restrict_by_distributors": bool(visible_links),
        }

    async def _filter_for_user(
        self,
        *,
        items: list[dict[str, Any]],
        user_distributor_id: uuid.UUID | None,
    ) -> list[dict[str, Any]]:
        if not items:
            return items

        prize_ids = [uuid.UUID(item["id"]) for item in items]
        links = (
            await self.db.scalars(
                select(PrizeDistributor).where(PrizeDistributor.prize_id.in_(prize_ids))
            )
        ).all()

        by_prize: dict[uuid.UUID, list[PrizeDistributor]] = {}
        for link in links:
            by_prize.setdefault(link.prize_id, []).append(link)

        filtered: list[dict[str, Any]] = []
        for item in items:
            prize_id = uuid.UUID(item["id"])
            prize_links = by_prize.get(prize_id, [])
            visible_links = [link for link in prize_links if link.is_visible]
            if not visible_links:
                filtered.append(item)
                continue

            if user_distributor_id is None:
                continue

            visible_for_user = any(
                link.distributor_id == user_distributor_id for link in visible_links
            )
            if visible_for_user:
                filtered.append(item)

        return filtered
