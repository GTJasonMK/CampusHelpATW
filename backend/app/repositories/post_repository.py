from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import Post, PostComment, PostLike, User


class PostRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, author_id: int, title: str, content: str, category: str) -> Post:
        post = Post(
            author_id=author_id,
            category=category,
            title=title,
            content=content,
            status="NORMAL",
        )
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def get_by_id(self, post_id: int) -> Post | None:
        return (await self.db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()

    async def list(
        self,
        page: int,
        page_size: int,
        category: str | None = None,
        sort: str = "latest",
        keyword: str | None = None,
        author_id: int | None = None,
    ) -> tuple[list[Post], int]:
        where_clauses = [Post.status == "NORMAL"]
        normalized_category = str(category or "").strip().upper()
        if normalized_category:
            where_clauses.append(Post.category == normalized_category)
        normalized_keyword = str(keyword or "").strip()
        if normalized_keyword:
            like_value = f"%{normalized_keyword}%"
            author_match_subquery = select(User.id).where(
                or_(
                    User.nickname.like(like_value),
                    User.campus_email.like(like_value),
                )
            )
            where_clauses.append(
                or_(
                    Post.title.like(like_value),
                    Post.content.like(like_value),
                    Post.author_id.in_(author_match_subquery),
                )
            )
        if author_id is not None and int(author_id) > 0:
            where_clauses.append(Post.author_id == int(author_id))

        where_cond = and_(*where_clauses)
        count_stmt = select(func.count(Post.id)).where(where_cond)
        data_stmt = select(Post).where(where_cond)

        normalized_sort = str(sort or "latest").strip().lower()
        if normalized_sort == "hot":
            data_stmt = data_stmt.order_by(
                Post.comment_count.desc(),
                Post.like_count.desc(),
                Post.view_count.desc(),
                Post.created_at.desc(),
                Post.id.desc(),
            )
        else:
            data_stmt = data_stmt.order_by(Post.created_at.desc(), Post.id.desc())

        data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def list_for_admin(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        category: str | None = None,
        sort: str = "latest",
        keyword: str | None = None,
        author_id: int | None = None,
    ) -> tuple[list[Post], int]:
        where_clauses = []
        normalized_status = str(status or "").strip().upper()
        if normalized_status:
            where_clauses.append(Post.status == normalized_status)

        normalized_category = str(category or "").strip().upper()
        if normalized_category:
            where_clauses.append(Post.category == normalized_category)

        normalized_keyword = str(keyword or "").strip()
        if normalized_keyword:
            like_value = f"%{normalized_keyword}%"
            author_match_subquery = select(User.id).where(
                or_(
                    User.nickname.like(like_value),
                    User.campus_email.like(like_value),
                )
            )
            where_clauses.append(
                or_(
                    Post.title.like(like_value),
                    Post.content.like(like_value),
                    Post.author_id.in_(author_match_subquery),
                )
            )

        if author_id is not None and int(author_id) > 0:
            where_clauses.append(Post.author_id == int(author_id))

        count_stmt = select(func.count(Post.id))
        data_stmt = select(Post)
        if where_clauses:
            where_cond = and_(*where_clauses)
            count_stmt = count_stmt.where(where_cond)
            data_stmt = data_stmt.where(where_cond)

        normalized_sort = str(sort or "latest").strip().lower()
        if normalized_sort == "hot":
            data_stmt = data_stmt.order_by(
                Post.comment_count.desc(),
                Post.like_count.desc(),
                Post.view_count.desc(),
                Post.created_at.desc(),
                Post.id.desc(),
            )
        else:
            data_stmt = data_stmt.order_by(Post.created_at.desc(), Post.id.desc())

        data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def create_comment(self, post: Post, author_id: int, content: str) -> PostComment:
        comment = PostComment(post_id=post.id, author_id=author_id, content=content)
        self.db.add(comment)
        post.comment_count += 1
        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def list_comments(self, post_id: int, page: int, page_size: int) -> tuple[list[PostComment], int]:
        where_cond = PostComment.post_id == int(post_id)
        count_stmt = select(func.count(PostComment.id)).where(where_cond)
        data_stmt = (
            select(PostComment)
            .where(where_cond)
            .order_by(PostComment.created_at.desc(), PostComment.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def get_like(self, post_id: int, user_id: int) -> PostLike | None:
        stmt = select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_liked_post_ids(self, user_id: int, post_ids: list[int]) -> set[int]:
        if not post_ids:
            return set()
        stmt = select(PostLike.post_id).where(
            PostLike.user_id == int(user_id),
            PostLike.post_id.in_(post_ids),
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return {int(item) for item in rows}

    async def create_like(self, post: Post, user_id: int) -> None:
        like = PostLike(post_id=post.id, user_id=user_id)
        self.db.add(like)
        post.like_count += 1
        await self.db.commit()

    async def remove_like(self, post: Post, like: PostLike) -> None:
        await self.db.delete(like)
        post.like_count = max(0, post.like_count - 1)
        await self.db.commit()

    async def soft_delete(self, post: Post) -> None:
        post.status = "DELETED"
        await self.db.commit()

    async def update_status(self, post: Post, status: str) -> Post:
        post.status = str(status or "").strip().upper()
        await self.db.commit()
        await self.db.refresh(post)
        return post

    async def increase_view_count(self, post: Post) -> None:
        post.view_count = max(0, int(post.view_count or 0)) + 1
        await self.db.commit()
        await self.db.refresh(post)
