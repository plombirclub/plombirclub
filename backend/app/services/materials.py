import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MaterialContentType, MaterialProgressStatus, UserRole
from app.models.material import Material
from app.models.user import User
from app.models.user_actions_log import UserActionsLog
from app.models.user_material_progress import UserMaterialProgress
from app.services.users import write_admin_log

STATUS_LABELS = {
    MaterialProgressStatus.not_started: "Не начат",
    MaterialProgressStatus.started: "Начат",
    MaterialProgressStatus.completed: "Изучен",
}


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _effective_total_pages(material: Material) -> int:
    if material.total_pages and material.total_pages > 0:
        return material.total_pages
    if material.content_type in {MaterialContentType.text, MaterialContentType.image}:
        return 1
    return 0


def _extract_viewed_pages(pages_viewed: dict[str, Any] | None) -> set[int]:
    if not pages_viewed:
        return set()
    raw_pages = pages_viewed.get("viewed", [])
    if not isinstance(raw_pages, list):
        return set()
    return {int(page) for page in raw_pages if isinstance(page, int) and page > 0}


def _serialize_progress(progress: UserMaterialProgress | None) -> dict[str, Any]:
    status = progress.status if progress else MaterialProgressStatus.not_started
    return {
        "status": status.value,
        "status_label": STATUS_LABELS[status],
        "pages_viewed": progress.pages_viewed if progress else {"viewed": []},
        "total_pages": progress.total_pages if progress else None,
        "started_at": progress.started_at.isoformat() if progress and progress.started_at else None,
        "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None,
        "updated_at": progress.updated_at.isoformat() if progress and progress.updated_at else None,
    }


def _serialize_material(
    material: Material,
    *,
    progress: UserMaterialProgress | None = None,
    stats: dict[str, int] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(material.id),
        "title": material.title,
        "description": material.description,
        "content_type": material.content_type.value,
        "file_path": material.file_path,
        "total_pages": material.total_pages,
        "is_published": material.is_published,
        "sort_order": material.sort_order,
        "created_at": material.created_at.isoformat() if material.created_at else None,
        "updated_at": material.updated_at.isoformat() if material.updated_at else None,
        "progress": _serialize_progress(progress),
    }
    if stats is not None:
        payload["stats"] = stats
    return payload


class MaterialsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_materials(
        self,
        *,
        user: User,
        include_unpublished: bool = False,
    ) -> dict[str, Any]:
        is_admin = user.role == UserRole.admin
        show_unpublished = include_unpublished and is_admin

        query = select(Material).order_by(Material.sort_order.asc(), Material.created_at.asc())
        if not show_unpublished:
            query = query.where(Material.is_published.is_(True))

        materials = (await self.db.scalars(query)).all()
        progress_map = await self._get_progress_map(user.id, [item.id for item in materials])

        items = [
            _serialize_material(
                material,
                progress=progress_map.get(material.id),
                stats=await self._material_stats(material.id) if is_admin else None,
            )
            for material in materials
        ]

        published_count = len([item for item in materials if item.is_published])
        completed_count = sum(
            1
            for material in materials
            if material.is_published
            and progress_map.get(material.id) is not None
            and progress_map[material.id].status == MaterialProgressStatus.completed
        )

        return {
            "items": items,
            "completed_count": completed_count,
            "published_count": published_count,
            "counter_label": f"Изучено материалов: {completed_count} / {published_count}",
        }

    async def get_material(
        self,
        *,
        user: User,
        material_id: uuid.UUID,
    ) -> dict[str, Any]:
        material = await self.db.scalar(select(Material).where(Material.id == material_id))
        if material is None:
            raise LookupError("Материал не найден")

        is_admin = user.role == UserRole.admin
        if not material.is_published and not is_admin:
            raise LookupError("Материал не найден")

        progress = await self.db.scalar(
            select(UserMaterialProgress).where(
                UserMaterialProgress.user_id == user.id,
                UserMaterialProgress.material_id == material.id,
            )
        )
        stats = await self._material_stats(material.id) if is_admin else None
        return _serialize_material(material, progress=progress, stats=stats)

    async def update_progress(
        self,
        *,
        user: User,
        material_id: uuid.UUID,
        action: str,
        page: int | None = None,
        video_percent: float | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        material = await self.db.scalar(
            select(Material).where(
                Material.id == material_id,
                Material.is_published.is_(True),
            )
        )
        if material is None:
            raise LookupError("Материал не найден")

        progress = await self.db.scalar(
            select(UserMaterialProgress).where(
                UserMaterialProgress.user_id == user.id,
                UserMaterialProgress.material_id == material.id,
            )
        )

        now = datetime.now(UTC)
        if progress is None:
            progress = UserMaterialProgress(
                user_id=user.id,
                material_id=material.id,
                status=MaterialProgressStatus.not_started,
                pages_viewed={"viewed": []},
                total_pages=_effective_total_pages(material) or None,
            )
            self.db.add(progress)

        if progress.status == MaterialProgressStatus.completed:
            return {
                "material_id": str(material.id),
                "progress": _serialize_progress(progress),
                "already_completed": True,
            }

        normalized_action = action.strip().lower()
        if normalized_action == "open":
            if progress.status == MaterialProgressStatus.not_started:
                progress.status = MaterialProgressStatus.started
                progress.started_at = now
            self._maybe_complete_on_open(material, progress)
        elif normalized_action == "view_page":
            if progress.status == MaterialProgressStatus.not_started:
                progress.status = MaterialProgressStatus.started
                progress.started_at = now
            if page is None or page < 1:
                raise ValueError("Укажите номер страницы или слайда")
            viewed = _extract_viewed_pages(progress.pages_viewed)
            viewed.add(page)
            progress.pages_viewed = {"viewed": sorted(viewed)}
            self._maybe_complete_by_pages(material, progress, viewed)
        elif normalized_action == "view_video":
            if progress.status == MaterialProgressStatus.not_started:
                progress.status = MaterialProgressStatus.started
                progress.started_at = now
            if video_percent is None:
                raise ValueError("Укажите процент просмотра видео")
            if video_percent >= 95:
                progress.status = MaterialProgressStatus.completed
                progress.completed_at = now
        else:
            raise ValueError("Недопустимое действие прогресса")

        progress.updated_at = now
        self.db.add(
            UserActionsLog(
                user_id=user.id,
                action=f"material_{normalized_action}",
                entity_type="material",
                entity_id=material.id,
                ip_address=ip_address,
            )
        )

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Не удалось сохранить прогресс материала") from None

        await self.db.refresh(progress)
        return {
            "material_id": str(material.id),
            "progress": _serialize_progress(progress),
            "already_completed": False,
        }

    async def create_material(
        self,
        *,
        admin: User,
        title: str,
        description: str | None,
        content_type: MaterialContentType,
        total_pages: int | None,
        sort_order: int,
        is_published: bool,
        file_path: str | None,
    ) -> dict[str, Any]:
        normalized_title = _normalize_text(title)
        if not normalized_title:
            raise ValueError("Название материала не может быть пустым")

        if content_type != MaterialContentType.text and not file_path:
            raise ValueError("Для выбранного типа материала нужен файл")

        if total_pages is not None and total_pages < 1:
            raise ValueError("Количество страниц должно быть больше нуля")

        material = Material(
            title=normalized_title,
            description=_normalize_text(description),
            content_type=content_type,
            file_path=file_path,
            total_pages=total_pages,
            sort_order=sort_order,
            is_published=is_published,
        )
        self.db.add(material)
        await self.db.flush()

        serialized = _serialize_material(material)
        await write_admin_log(
            self.db,
            admin=admin,
            action="create_material",
            entity_type="material",
            entity_id=material.id,
            new_value=serialized,
        )
        await self.db.commit()
        await self.db.refresh(material)
        return _serialize_material(material)

    async def update_material(
        self,
        *,
        admin: User,
        material_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        material = await self.db.scalar(select(Material).where(Material.id == material_id))
        if material is None:
            raise LookupError("Материал не найден")

        old_value = _serialize_material(material)

        if "title" in updates and updates["title"] is not None:
            normalized_title = _normalize_text(str(updates["title"]))
            if not normalized_title:
                raise ValueError("Название материала не может быть пустым")
            material.title = normalized_title

        if "description" in updates:
            material.description = _normalize_text(updates["description"])

        if "content_type" in updates and updates["content_type"] is not None:
            material.content_type = updates["content_type"]

        if "total_pages" in updates:
            total_pages = updates["total_pages"]
            if total_pages is not None and total_pages < 1:
                raise ValueError("Количество страниц должно быть больше нуля")
            material.total_pages = total_pages

        if "sort_order" in updates and updates["sort_order"] is not None:
            material.sort_order = int(updates["sort_order"])

        if "is_published" in updates and updates["is_published"] is not None:
            material.is_published = bool(updates["is_published"])

        if "file_path" in updates:
            material.file_path = updates["file_path"]

        if material.content_type != MaterialContentType.text and not material.file_path:
            raise ValueError("Для выбранного типа материала нужен файл")

        new_value = _serialize_material(material)
        await write_admin_log(
            self.db,
            admin=admin,
            action="update_material",
            entity_type="material",
            entity_id=material.id,
            old_value=old_value,
            new_value=new_value,
        )
        await self.db.commit()
        await self.db.refresh(material)
        return _serialize_material(material, stats=await self._material_stats(material.id))

    async def hide_material(self, *, admin: User, material_id: uuid.UUID) -> dict[str, Any]:
        material = await self.db.scalar(select(Material).where(Material.id == material_id))
        if material is None:
            raise LookupError("Материал не найден")

        old_value = _serialize_material(material)
        material.is_published = False
        new_value = _serialize_material(material)

        await write_admin_log(
            self.db,
            admin=admin,
            action="hide_material",
            entity_type="material",
            entity_id=material.id,
            old_value=old_value,
            new_value=new_value,
        )
        await self.db.commit()
        await self.db.refresh(material)
        return new_value

    async def _get_progress_map(
        self,
        user_id: uuid.UUID,
        material_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, UserMaterialProgress]:
        if not material_ids:
            return {}

        rows = (
            await self.db.scalars(
                select(UserMaterialProgress).where(
                    UserMaterialProgress.user_id == user_id,
                    UserMaterialProgress.material_id.in_(material_ids),
                )
            )
        ).all()
        return {row.material_id: row for row in rows}

    async def _material_stats(self, material_id: uuid.UUID) -> dict[str, int]:
        active_users_count = int(
            (await self.db.scalar(
                select(func.count(User.id)).where(
                    User.role == UserRole.user,
                    User.is_active.is_(True),
                )
            ))
            or 0
        )

        rows = (
            await self.db.execute(
                select(
                    UserMaterialProgress.status,
                    func.count(UserMaterialProgress.id),
                )
                .where(UserMaterialProgress.material_id == material_id)
                .group_by(UserMaterialProgress.status)
            )
        ).all()

        counts = {status: count for status, count in rows}
        started = int(counts.get(MaterialProgressStatus.started, 0))
        completed = int(counts.get(MaterialProgressStatus.completed, 0))
        with_progress = started + completed
        not_started = max(active_users_count - with_progress, 0)

        return {
            "not_started": not_started,
            "started": started,
            "completed": completed,
            "total_users": active_users_count,
        }

    def _maybe_complete_on_open(self, material: Material, progress: UserMaterialProgress) -> None:
        if material.content_type == MaterialContentType.video:
            return
        total_pages = _effective_total_pages(material)
        if total_pages == 1:
            progress.status = MaterialProgressStatus.completed
            progress.completed_at = datetime.now(UTC)
            progress.pages_viewed = {"viewed": [1]}

    def _maybe_complete_by_pages(
        self,
        material: Material,
        progress: UserMaterialProgress,
        viewed: set[int],
    ) -> None:
        total_pages = _effective_total_pages(material)
        if total_pages <= 0:
            return
        expected_pages = set(range(1, total_pages + 1))
        if expected_pages.issubset(viewed):
            progress.status = MaterialProgressStatus.completed
            progress.completed_at = datetime.now(UTC)
