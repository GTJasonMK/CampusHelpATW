from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import AdminRole, AdminUserRole, User

UNSET = object()


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        return (await self.db.execute(select(User).where(User.campus_email == email))).scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    async def list_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        stmt = select(User).where(User.id.in_(user_ids))
        return list((await self.db.execute(stmt)).scalars().all())

    async def search_active_users(
        self,
        exclude_user_id: int,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        where_clauses = [
            User.status == "ACTIVE",
            User.id != exclude_user_id,
        ]
        normalized_keyword = (keyword or "").strip()
        if normalized_keyword:
            like_value = f"%{normalized_keyword}%"
            where_clauses.append(
                or_(
                    User.nickname.like(like_value),
                    User.campus_email.like(like_value),
                    User.school_name.like(like_value),
                    User.college_name.like(like_value),
                )
            )

        where_cond = and_(*where_clauses)
        count_stmt = select(func.count(User.id)).where(where_cond)
        data_stmt = (
            select(User)
            .where(where_cond)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def update_profile(
        self,
        user: User,
        nickname: str | None | object = UNSET,
        avatar_url: str | None | object = UNSET,
        college_name: str | None | object = UNSET,
    ) -> User:
        if nickname is not UNSET:
            user.nickname = nickname
        if avatar_url is not UNSET:
            user.avatar_url = avatar_url
        if college_name is not UNSET:
            user.college_name = college_name
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def list_role_codes(self, user_id: int) -> list[str]:
        role_query = (
            select(AdminRole.role_code)
            .join(AdminUserRole, AdminUserRole.role_id == AdminRole.id)
            .where(AdminUserRole.user_id == user_id)
        )
        return list((await self.db.execute(role_query)).scalars().all())
