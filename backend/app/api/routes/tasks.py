from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import LimitRule, rate_limiter
from app.core.response import ok
from app.core.security import get_current_user
from app.core.settings import get_settings
from app.db_models import User
from app.repositories.user_repository import UserRepository
from app.schemas import (
    TaskActionReasonRequest,
    TaskCreateRequest,
    TaskOut,
    TaskReviewRequest,
    TaskStatusLogOut,
    TaskUpdateRequest,
)
from app.services import (
    accept_task,
    cancel_task,
    confirm_task_completion,
    create_task,
    create_task_review,
    dispute_task,
    get_user_public_profile,
    get_task_or_404,
    get_task_unread_summary,
    list_my_points,
    list_shared_tasks_between_users,
    list_task_status_logs,
    list_tasks,
    list_user_reviews,
    start_task,
    submit_task_completion,
    update_task,
)
from app.ws.notifier import push_task_event_to_participants

router = APIRouter(prefix="/tasks", tags=["tasks"])
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


async def _notify_task_event(
    db: AsyncSession,
    task_id: int,
    action: str,
    operator: User,
    reason: str | None = None,
) -> None:
    try:
        task = await get_task_or_404(db, task_id)
        await push_task_event_to_participants(
            participant_user_ids=[task.publisher_id, task.acceptor_id],
            task_id=task.id,
            status=task.status,
            action=action,
            operator_user_id=operator.id,
            reason=reason,
        )
    except Exception:
        # 通知失败不阻断主流程。
        pass


@router.post("")
async def create_task_endpoint(
    payload: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    rate_limiter.hit(
        user_id=current_user.id,
        rule=LimitRule(
            key="task_publish",
            max_count=settings.task_publish_rate_limit_count,
            window_seconds=settings.task_publish_rate_limit_window_seconds,
        ),
    )
    task = await create_task(db=db, user=current_user, payload=payload)
    return ok(data=TaskOut.model_validate(task).model_dump())


@router.get("")
async def list_tasks_endpoint(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    role: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_unread: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    publisher_id = None
    acceptor_id = None
    participant_id = None
    normalized_role = str(role or "").strip().lower()
    if normalized_role == "publisher":
        publisher_id = int(current_user.id)
    elif normalized_role == "acceptor":
        acceptor_id = int(current_user.id)
    elif normalized_role == "mine":
        participant_id = int(current_user.id)

    data = await list_tasks(
        db=db,
        status=status,
        category=category,
        page=page,
        page_size=page_size,
        current_user=current_user,
        include_unread=include_unread,
        keyword=keyword,
        publisher_id=publisher_id,
        acceptor_id=acceptor_id,
        participant_id=participant_id,
    )
    unread_map = data.pop("task_unread_map", {})
    task_items = data.get("list") or []
    participant_user_ids: set[int] = set()
    for item in task_items:
        participant_user_ids.add(int(item.publisher_id))
        if item.acceptor_id:
            participant_user_ids.add(int(item.acceptor_id))
    users = await UserRepository(db).list_by_ids(sorted(participant_user_ids))
    user_map = {int(item.id): item for item in users}

    payload_list = []
    for item in task_items:
        payload = TaskOut.model_validate(item).model_dump()
        payload["unread_count"] = int(unread_map.get(item.id, 0)) if include_unread else None
        payload["publisher_user"] = _to_user_brief(user_map.get(int(item.publisher_id)))
        payload["acceptor_user"] = _to_user_brief(user_map.get(int(item.acceptor_id))) if item.acceptor_id else None
        payload_list.append(payload)
    data["list"] = payload_list

    if not include_unread and "total_unread" in data:
        data.pop("total_unread", None)
    return ok(data=data)


@router.patch("/{task_id}")
async def update_task_endpoint(
    task_id: int,
    payload: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    task = await update_task(db=db, task_id=task_id, operator=current_user, payload=payload)
    return ok(data=TaskOut.model_validate(task).model_dump())


@router.get("/{task_id}")
async def get_task_endpoint(
    task_id: int,
    include_unread: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    task = await get_task_or_404(db, task_id)
    payload = TaskOut.model_validate(task).model_dump()
    participant_ids = [int(task.publisher_id)]
    if task.acceptor_id:
        participant_ids.append(int(task.acceptor_id))
    users = await UserRepository(db).list_by_ids(participant_ids)
    user_map = {int(item.id): item for item in users}
    payload["publisher_user"] = _to_user_brief(user_map.get(int(task.publisher_id)))
    payload["acceptor_user"] = _to_user_brief(user_map.get(int(task.acceptor_id))) if task.acceptor_id else None
    if include_unread:
        unread_data = await get_task_unread_summary(db=db, user=current_user, task_id=task_id)
        payload["unread_count"] = int(unread_data.get("unread_count", 0))
    return ok(data=payload)


@router.get("/{task_id}/status-logs")
async def list_task_status_logs_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    logs = await list_task_status_logs(db, task_id)
    return ok(data=[TaskStatusLogOut.model_validate(item).model_dump() for item in logs])


@router.post("/{task_id}/accept")
async def accept_task_endpoint(
    task_id: int,
    payload: TaskActionReasonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await accept_task(db=db, task_id=task_id, operator=current_user, payload=payload)
    await _notify_task_event(
        db=db,
        task_id=task_id,
        action="accept",
        operator=current_user,
        reason=payload.reason,
    )
    return ok(data={"task_id": task_id, "status": "ACCEPTED"})


@router.post("/{task_id}/start")
async def start_task_endpoint(
    task_id: int,
    payload: TaskActionReasonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await start_task(db=db, task_id=task_id, operator=current_user, payload=payload)
    await _notify_task_event(
        db=db,
        task_id=task_id,
        action="start",
        operator=current_user,
        reason=payload.reason,
    )
    return ok(data={"task_id": task_id, "status": "IN_PROGRESS"})


@router.post("/{task_id}/submit-completion")
async def submit_completion_endpoint(
    task_id: int,
    payload: TaskActionReasonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await submit_task_completion(db=db, task_id=task_id, operator=current_user, payload=payload)
    await _notify_task_event(
        db=db,
        task_id=task_id,
        action="submit_completion",
        operator=current_user,
        reason=payload.reason,
    )
    return ok(data={"task_id": task_id, "status": "PENDING_CONFIRM"})


@router.post("/{task_id}/confirm-completion")
async def confirm_completion_endpoint(
    task_id: int,
    payload: TaskActionReasonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await confirm_task_completion(db=db, task_id=task_id, operator=current_user, payload=payload)
    await _notify_task_event(
        db=db,
        task_id=task_id,
        action="confirm_completion",
        operator=current_user,
        reason=payload.reason,
    )
    return ok(data={"task_id": task_id, "status": "DONE"})


@router.post("/{task_id}/dispute")
async def dispute_task_endpoint(
    task_id: int,
    payload: TaskActionReasonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await dispute_task(db=db, task_id=task_id, operator=current_user, payload=payload)
    await _notify_task_event(
        db=db,
        task_id=task_id,
        action="dispute",
        operator=current_user,
        reason=payload.reason,
    )
    return ok(data={"task_id": task_id, "status": "DISPUTED"})


@router.post("/{task_id}/cancel")
async def cancel_task_endpoint(
    task_id: int,
    payload: TaskActionReasonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await cancel_task(db=db, task_id=task_id, operator=current_user, payload=payload)
    await _notify_task_event(
        db=db,
        task_id=task_id,
        action="cancel",
        operator=current_user,
        reason=payload.reason,
    )
    return ok(data={"task_id": task_id, "status": "CANCELED"})


@router.post("/{task_id}/reviews")
async def create_task_review_endpoint(
    task_id: int,
    payload: TaskReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    review = await create_task_review(db=db, task_id=task_id, operator=current_user, payload=payload)
    return ok(
        data={
            "id": review.id,
            "task_id": review.task_id,
            "reviewer_id": review.reviewer_id,
            "reviewee_id": review.reviewee_id,
            "rating": review.rating,
            "content": review.content,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }
    )


aux_router = APIRouter(tags=["tasks"])


@aux_router.get("/users/{user_id}")
async def get_user_public_profile_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await get_user_public_profile(
        db=db,
        current_user=current_user,
        target_user_id=user_id,
    )
    return ok(data=data)


@aux_router.get("/users/{user_id}/reviews")
async def list_user_reviews_endpoint(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    rating: int | None = Query(default=None, ge=1, le=5),
    with_content: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    data = await list_user_reviews(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        rating=rating,
        with_content=with_content,
    )
    data["list"] = [
        {
            "id": item.id,
            "task_id": item.task_id,
            "reviewer_id": item.reviewer_id,
            "reviewee_id": item.reviewee_id,
            "rating": item.rating,
            "content": item.content,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in data["list"]
    ]
    return ok(data=data)


@aux_router.get("/users/{user_id}/shared/tasks")
async def list_shared_tasks_endpoint(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    sort: str = Query(default="latest"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await list_shared_tasks_between_users(
        db=db,
        current_user=current_user,
        target_user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
        sort=sort,
    )
    return ok(data=data)


@aux_router.get("/me/points/ledger")
async def list_my_points_endpoint(
    point_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await list_my_points(
        db=db,
        user_id=current_user.id,
        point_type=point_type,
        page=page,
        page_size=page_size,
    )
    data["list"] = [
        {
            "id": item.id,
            "user_id": item.user_id,
            "point_type": item.point_type,
            "change_amount": item.change_amount,
            "balance_after": item.balance_after,
            "biz_type": item.biz_type,
            "biz_id": item.biz_id,
            "remark": item.remark,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in data["list"]
    ]
    return ok(data=data)
