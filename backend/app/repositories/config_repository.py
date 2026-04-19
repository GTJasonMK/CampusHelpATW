from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import SystemConfig, TaskCategory


class ConfigRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_task_categories(
        self,
        page: int | None = None,
        page_size: int | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[TaskCategory], int]:
        filters = []
        if is_active is not None:
            filters.append(TaskCategory.is_active == is_active)

        count_stmt = select(func.count(TaskCategory.id))
        data_stmt = select(TaskCategory).order_by(TaskCategory.sort_order.asc(), TaskCategory.id.asc())
        if filters:
            for cond in filters:
                count_stmt = count_stmt.where(cond)
                data_stmt = data_stmt.where(cond)

        if page is not None and page_size is not None:
            data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)

        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def get_task_category_by_id(self, category_id: int) -> TaskCategory | None:
        stmt = select(TaskCategory).where(TaskCategory.id == category_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_task_category_by_code(self, code: str) -> TaskCategory | None:
        stmt = select(TaskCategory).where(TaskCategory.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_task_category(
        self,
        code: str,
        name: str,
        sort_order: int,
        is_active: bool,
    ) -> TaskCategory:
        item = TaskCategory(
            code=code,
            name=name,
            sort_order=sort_order,
            is_active=is_active,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_task_category(
        self,
        item: TaskCategory,
        code: str | None = None,
        name: str | None = None,
        sort_order: int | None = None,
        is_active: bool | None = None,
    ) -> TaskCategory:
        if code is not None:
            item.code = code
        if name is not None:
            item.name = name
        if sort_order is not None:
            item.sort_order = sort_order
        if is_active is not None:
            item.is_active = is_active
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_system_configs(
        self,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[SystemConfig], int]:
        count_stmt = select(func.count(SystemConfig.id))
        data_stmt = select(SystemConfig).order_by(SystemConfig.config_key.asc(), SystemConfig.id.asc())
        if page is not None and page_size is not None:
            data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def get_system_config_by_key(self, config_key: str) -> SystemConfig | None:
        stmt = select(SystemConfig).where(SystemConfig.config_key == config_key)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def upsert_system_config(
        self,
        config_key: str,
        config_value: Any,
        description: str | None = None,
    ) -> SystemConfig:
        item = await self.get_system_config_by_key(config_key)
        if item is None:
            item = SystemConfig(
                config_key=config_key,
                config_value=config_value,
                description=description,
            )
            self.db.add(item)
        else:
            item.config_value = config_value
            if description is not None:
                item.description = description
        await self.db.commit()
        await self.db.refresh(item)
        return item
