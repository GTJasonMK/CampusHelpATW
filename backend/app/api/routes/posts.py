from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import LimitRule, rate_limiter
from app.core.response import ok
from app.core.security import get_current_user
from app.core.settings import get_settings
from app.db_models import User
from app.schemas import PostCommentCreateRequest, PostCreateRequest
from app.repositories.user_repository import UserRepository
from app.services import (
    create_post,
    create_post_comment,
    delete_post,
    get_post_detail,
    like_post,
    list_my_posts,
    list_post_comments,
    list_posts,
    unlike_post,
)

router = APIRouter(prefix="/posts", tags=["posts"])
settings = get_settings()


def _to_user_brief(user: User | None) -> dict | None:
    if user is None:
        return None
    return {
        "id": int(user.id),
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "school_name": user.school_name,
        "college_name": user.college_name,
        "status": user.status,
    }


def _to_post_payload(
    post,
    author_user: User | None,
    liked_by_me: bool,
) -> dict:
    return {
        "id": int(post.id),
        "author_id": int(post.author_id),
        "author_user": _to_user_brief(author_user),
        "category": post.category,
        "title": post.title,
        "content": post.content,
        "like_count": int(post.like_count or 0),
        "comment_count": int(post.comment_count or 0),
        "view_count": int(post.view_count or 0),
        "liked_by_me": bool(liked_by_me),
        "status": post.status,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


def _to_comment_payload(comment, author_user: User | None) -> dict:
    return {
        "id": int(comment.id),
        "post_id": int(comment.post_id),
        "author_id": int(comment.author_id),
        "author_user": _to_user_brief(author_user),
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@router.post("")
async def create_post_endpoint(
    payload: PostCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    rate_limiter.hit(
        user_id=current_user.id,
        rule=LimitRule(
            key="post_publish",
            max_count=settings.post_publish_rate_limit_count,
            window_seconds=settings.post_publish_rate_limit_window_seconds,
        ),
    )
    post = await create_post(db=db, author=current_user, payload=payload)
    return ok(data=_to_post_payload(post, author_user=current_user, liked_by_me=False))


@router.get("/mine")
async def list_my_posts_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    sort: str = Query(default="latest"),
    keyword: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await list_my_posts(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        category=category,
        sort=sort,
        keyword=keyword,
    )
    liked_post_id_set = {int(item) for item in data.pop("liked_post_ids", [])}
    data["list"] = [
        _to_post_payload(
            post=item,
            author_user=current_user,
            liked_by_me=int(item.id) in liked_post_id_set,
        )
        for item in data["list"]
    ]
    return ok(data=data)


@router.get("")
async def list_posts_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    sort: str = Query(default="latest"),
    keyword: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await list_posts(
        db=db,
        page=page,
        page_size=page_size,
        current_user=current_user,
        category=category,
        sort=sort,
        keyword=keyword,
    )
    items = data.get("list") or []
    liked_post_id_set = {int(item) for item in data.pop("liked_post_ids", [])}
    author_ids = sorted({int(item.author_id) for item in items})
    users = await UserRepository(db).list_by_ids(author_ids)
    user_map = {int(item.id): item for item in users}
    data["list"] = [
        _to_post_payload(
            post=item,
            author_user=user_map.get(int(item.author_id)),
            liked_by_me=int(item.id) in liked_post_id_set,
        )
        for item in items
    ]
    return ok(data=data)


@router.get("/{post_id}")
async def get_post_endpoint(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await get_post_detail(db=db, post_id=post_id, current_user=current_user)
    post = data["post"]
    author_user = await UserRepository(db).get_by_id(int(post.author_id))
    return ok(data=_to_post_payload(post, author_user=author_user, liked_by_me=bool(data["liked_by_me"])))


@router.get("/{post_id}/comments")
async def list_comments_endpoint(
    post_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    data = await list_post_comments(
        db=db,
        post_id=post_id,
        page=page,
        page_size=page_size,
    )
    comments = data.get("list") or []
    author_ids = sorted({int(item.author_id) for item in comments})
    users = await UserRepository(db).list_by_ids(author_ids)
    user_map = {int(item.id): item for item in users}
    data["list"] = [
        _to_comment_payload(
            comment=item,
            author_user=user_map.get(int(item.author_id)),
        )
        for item in comments
    ]
    return ok(data=data)


@router.post("/{post_id}/comments")
async def create_comment_endpoint(
    post_id: int,
    payload: PostCommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    comment = await create_post_comment(db=db, post_id=post_id, author=current_user, payload=payload)
    return ok(data=_to_comment_payload(comment, author_user=current_user))


@router.post("/{post_id}/like")
async def like_post_endpoint(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await like_post(db=db, post_id=post_id, user=current_user)
    return ok(data={"post_id": post_id, "liked": True})


@router.delete("/{post_id}/like")
async def unlike_post_endpoint(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await unlike_post(db=db, post_id=post_id, user=current_user)
    return ok(data={"post_id": post_id, "liked": False})


@router.delete("/{post_id}")
async def delete_post_endpoint(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await delete_post(db=db, post_id=post_id, user=current_user)
    return ok(data={"id": int(post_id), "deleted": True})
