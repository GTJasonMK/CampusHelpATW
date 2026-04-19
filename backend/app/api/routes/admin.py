from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ok
from app.core.security import get_current_user
from app.db_models import User
from app.schemas import (
    AdminArbitrateRequest,
    AdminPostStatusPatchRequest,
    ReportHandleRequest,
    SystemConfigUpsertRequest,
    TaskCategoryCreateRequest,
    TaskCategoryPatchRequest,
)
from app.services import (
    arbitrate_task,
    create_admin_task_category,
    get_admin_school_branding_config,
    get_task_or_404,
    handle_report,
    list_admin_posts,
    list_admin_reports,
    list_admin_system_configs,
    list_admin_task_categories,
    list_admin_tasks,
    patch_admin_post_status,
    patch_admin_task_category,
    put_admin_school_branding_config,
    put_admin_system_config,
    require_admin,
)
from app.repositories.user_repository import UserRepository
from app.ws.notifier import push_task_event_to_participants

router = APIRouter(prefix="/admin", tags=["admin"])


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


def _to_post_payload(post, author_user: User | None) -> dict:
    return {
        "id": int(post.id),
        "author_id": int(post.author_id),
        "author_user": _to_user_brief(author_user),
        "category": post.category,
        "title": post.title,
        "content": post.content,
        "status": post.status,
        "like_count": int(post.like_count or 0),
        "comment_count": int(post.comment_count or 0),
        "view_count": int(post.view_count or 0),
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


@router.get("/reports")
async def list_admin_reports_endpoint(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    data = await list_admin_reports(db=db, status=status, page=page, page_size=page_size)
    data["list"] = [
        {
            "id": item.id,
            "reporter_id": item.reporter_id,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "reason_code": item.reason_code,
            "reason_text": item.reason_text,
            "status": item.status,
            "handler_admin_id": item.handler_admin_id,
            "handle_result": item.handle_result,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "handled_at": item.handled_at.isoformat() if item.handled_at else None,
        }
        for item in data["list"]
    ]
    return ok(data=data)


@router.post("/reports/{report_id}/handle")
async def handle_report_endpoint(
    report_id: int,
    payload: ReportHandleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    report = await handle_report(db=db, report_id=report_id, admin=current_user, payload=payload)
    return ok(
        data={
            "id": report.id,
            "status": report.status,
            "handler_admin_id": report.handler_admin_id,
            "handle_result": report.handle_result,
            "handled_at": report.handled_at.isoformat() if report.handled_at else None,
        }
    )


@router.post("/tasks/{task_id}/arbitrate")
async def arbitrate_task_endpoint(
    task_id: int,
    payload: AdminArbitrateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    await arbitrate_task(db=db, task_id=task_id, admin=current_user, payload=payload)
    try:
        task = await get_task_or_404(db, task_id)
        await push_task_event_to_participants(
            participant_user_ids=[task.publisher_id, task.acceptor_id],
            task_id=task.id,
            status=task.status,
            action="arbitrate",
            operator_user_id=current_user.id,
            reason=payload.reason,
            extra={"decision": payload.decision},
        )
    except Exception:
        # 通知失败不阻断主流程。
        pass
    return ok(data={"task_id": task_id, "decision": payload.decision})


@router.get("/tasks")
async def list_admin_tasks_endpoint(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    from app.schemas import TaskOut

    data = await list_admin_tasks(
        db=db,
        status=status,
        category=category,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = data.get("list") or []
    participant_user_ids: set[int] = set()
    for item in items:
        participant_user_ids.add(int(item.publisher_id))
        if item.acceptor_id:
            participant_user_ids.add(int(item.acceptor_id))
    users = await UserRepository(db).list_by_ids(sorted(participant_user_ids))
    user_map = {int(item.id): item for item in users}

    payload_list = []
    for item in items:
        payload = TaskOut.model_validate(item).model_dump()
        payload["publisher_user"] = _to_user_brief(user_map.get(int(item.publisher_id)))
        payload["acceptor_user"] = _to_user_brief(user_map.get(int(item.acceptor_id))) if item.acceptor_id else None
        payload_list.append(payload)
    data["list"] = payload_list
    return ok(data=data)


@router.get("/task-categories")
async def list_admin_task_categories_endpoint(
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    data = await list_admin_task_categories(
        db=db,
        page=page,
        page_size=page_size,
        is_active=is_active,
    )
    data["list"] = [
        {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "sort_order": item.sort_order,
            "is_active": bool(item.is_active),
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in data["list"]
    ]
    return ok(data=data)


@router.post("/task-categories")
async def create_admin_task_category_endpoint(
    payload: TaskCategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    item = await create_admin_task_category(db=db, admin=current_user, payload=payload)
    return ok(
        data={
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "sort_order": item.sort_order,
            "is_active": bool(item.is_active),
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
    )


@router.patch("/task-categories/{category_id}")
async def patch_admin_task_category_endpoint(
    category_id: int,
    payload: TaskCategoryPatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    item = await patch_admin_task_category(
        db=db,
        category_id=category_id,
        admin=current_user,
        payload=payload,
    )
    return ok(
        data={
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "sort_order": item.sort_order,
            "is_active": bool(item.is_active),
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
    )


@router.get("/system-configs")
async def list_admin_system_configs_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    data = await list_admin_system_configs(
        db=db,
        page=page,
        page_size=page_size,
    )
    data["list"] = [
        {
            "id": item.id,
            "config_key": item.config_key,
            "config_value": item.config_value,
            "description": item.description,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in data["list"]
    ]
    return ok(data=data)


@router.put("/system-configs/{config_key}")
async def put_admin_system_config_endpoint(
    config_key: str,
    payload: SystemConfigUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    item = await put_admin_system_config(
        db=db,
        admin=current_user,
        config_key=config_key,
        payload=payload,
    )
    return ok(
        data={
            "id": item.id,
            "config_key": item.config_key,
            "config_value": item.config_value,
            "description": item.description,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
    )


@router.get("/school-branding")
async def get_admin_school_branding_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    data = await get_admin_school_branding_config(db=db)
    return ok(data=data)


@router.put("/school-branding")
async def put_admin_school_branding_endpoint(
    payload: SystemConfigUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    data = await put_admin_school_branding_config(
        db=db,
        admin=current_user,
        payload=payload,
    )
    return ok(data=data)


@router.get("/posts")
async def list_admin_posts_endpoint(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    sort: str = Query(default="latest"),
    keyword: str | None = Query(default=None),
    author_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    data = await list_admin_posts(
        db=db,
        status=status,
        category=category,
        sort=sort,
        keyword=keyword,
        author_id=author_id,
        page=page,
        page_size=page_size,
    )
    items = data.get("list") or []
    author_ids = sorted({int(item.author_id) for item in items})
    users = await UserRepository(db).list_by_ids(author_ids)
    user_map = {int(item.id): item for item in users}
    data["list"] = [
        _to_post_payload(
            post=item,
            author_user=user_map.get(int(item.author_id)),
        )
        for item in items
    ]
    return ok(data=data)


@router.patch("/posts/{post_id}/status")
async def patch_admin_post_status_endpoint(
    post_id: int,
    payload: AdminPostStatusPatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await require_admin(db, current_user)
    post = await patch_admin_post_status(
        db=db,
        post_id=post_id,
        admin=current_user,
        status=payload.status,
        reason=payload.reason,
    )
    author_user = await UserRepository(db).get_by_id(int(post.author_id))
    return ok(data=_to_post_payload(post=post, author_user=author_user))
