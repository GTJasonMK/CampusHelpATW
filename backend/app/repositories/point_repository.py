from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import PointLedger, User


class PointRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _is_sqlite(self) -> bool:
        bind = self.db.get_bind()
        return bool(bind and bind.dialect.name == "sqlite")

    async def add_points(
        self,
        user_id: int,
        point_type: str,
        change_amount: int,
        biz_type: str,
        biz_id: int,
        remark: str,
    ) -> None:
        if self._is_sqlite():
            user = (await self.db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
            if user is None:
                raise ValueError("user not found")

            normalized_type = str(point_type or "").upper()
            normalized_change = int(change_amount or 0)
            if normalized_type == "HELP":
                balance_after = int(user.help_points_balance or 0) + normalized_change
                if balance_after < 0:
                    raise ValueError("insufficient HELP points")
                user.help_points_balance = balance_after
            elif normalized_type == "HONOR":
                balance_after = int(user.honor_points_balance or 0) + normalized_change
                if balance_after < 0:
                    raise ValueError("insufficient HONOR points")
                user.honor_points_balance = balance_after
            else:
                raise ValueError("invalid point type")

            self.db.add(
                PointLedger(
                    user_id=int(user_id),
                    point_type=normalized_type,
                    change_amount=normalized_change,
                    balance_after=balance_after,
                    biz_type=str(biz_type or ""),
                    biz_id=int(biz_id) if biz_id is not None else None,
                    remark=remark,
                )
            )
            await self.db.commit()
            return

        await self.db.execute(
            text(
                "CALL sp_add_points(:user_id, :point_type, :change_amount, :biz_type, :biz_id, :remark)"
            ),
            {
                "user_id": user_id,
                "point_type": point_type,
                "change_amount": change_amount,
                "biz_type": biz_type,
                "biz_id": biz_id,
                "remark": remark,
            },
        )
        await self.db.commit()

    async def list_user_points(
        self,
        user_id: int,
        point_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[PointLedger], int]:
        where_clauses = [PointLedger.user_id == user_id]
        if point_type:
            where_clauses.append(PointLedger.point_type == point_type)

        count_stmt = select(func.count(PointLedger.id)).where(and_(*where_clauses))
        data_stmt = (
            select(PointLedger)
            .where(and_(*where_clauses))
            .order_by(PointLedger.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)
