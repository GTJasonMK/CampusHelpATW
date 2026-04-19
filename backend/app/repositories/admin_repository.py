from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import AdminOperationLog


class AdminRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add_operation_log(
        self,
        admin_user_id: int,
        operation_type: str,
        target_type: str,
        target_id: int,
        detail: str | None,
    ) -> AdminOperationLog:
        log = AdminOperationLog(
            admin_user_id=admin_user_id,
            operation_type=operation_type,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

