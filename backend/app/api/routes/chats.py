from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ok
from app.core.security import get_current_user
from app.db_models import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.task_repository import TaskRepository
from app.schemas import ChatMessageCreateRequest, ChatMessageOut, ChatReadMarkRequest
from app.services import (
    create_chat_message,
    get_task_chat,
    get_transaction_channel_state,
    list_chat_messages,
    list_my_chat_unread,
    mark_chat_read,
)
from app.ws.notifier import push_chat_unread_to_participants

router = APIRouter(tags=["chats"])


@router.get("/tasks/{task_id}/chat")
async def get_task_chat_endpoint(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    chat = await get_task_chat(db=db, task_id=task_id, operator=current_user)
    task = await TaskRepository(db).get_by_id(chat.task_id)
    channel_state = get_transaction_channel_state(task)
    return ok(
        data={
            "id": chat.id,
            "chat_id": chat.id,
            "task_id": chat.task_id,
            "created_at": chat.created_at.isoformat() if chat.created_at else None,
            "task_status": channel_state["task_status"],
            "channel_open": channel_state["channel_open"],
            "channel_archived": channel_state["channel_archived"],
            "channel_reason": channel_state["reason"],
        }
    )


@router.get("/chats/{chat_id}/messages")
async def list_chat_messages_endpoint(
    chat_id: int,
    cursor: int = Query(default=0, ge=0),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    messages = await list_chat_messages(
        db=db,
        chat_id=chat_id,
        cursor=cursor,
        page_size=page_size,
        operator=current_user,
    )
    return ok(data=[ChatMessageOut.model_validate(item).model_dump() for item in messages])


@router.post("/chats/{chat_id}/messages")
async def create_chat_message_endpoint(
    chat_id: int,
    payload: ChatMessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    msg = await create_chat_message(
        db=db,
        chat_id=chat_id,
        sender=current_user,
        message_type=payload.message_type,
        content=payload.content,
    )
    try:
        chat = await ChatRepository(db).get_by_chat_id(msg.chat_id)
        if chat is not None:
            task = await TaskRepository(db).get_by_id(chat.task_id)
            if task is not None:
                reader_user_ids = await ChatRepository(db).list_reader_user_ids(chat.id)
                notify_user_ids = {
                    int(task.publisher_id or 0),
                    int(task.acceptor_id or 0),
                    *[int(item) for item in reader_user_ids],
                }
                await push_chat_unread_to_participants(
                    db=db,
                    participant_user_ids=sorted(notify_user_ids),
                    task_id=task.id,
                    reason="message_created_http",
                    chat_id=chat.id,
                    extra={
                        "sender_id": int(msg.sender_id),
                        "message_id": int(msg.id),
                    },
                )
    except Exception:
        # 通知推送失败不应影响消息主流程。
        pass
    return ok(data=ChatMessageOut.model_validate(msg).model_dump())


@router.get("/me/chats/unread")
async def list_my_chat_unread_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await list_my_chat_unread(db=db, user=current_user)
    return ok(data=data)


@router.post("/chats/{chat_id}/read")
async def mark_chat_read_endpoint(
    chat_id: int,
    payload: ChatReadMarkRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await mark_chat_read(
        db=db,
        chat_id=chat_id,
        operator=current_user,
        payload=payload,
    )
    try:
        task = await TaskRepository(db).get_by_id(int(data.get("task_id", 0)))
        if task is not None:
            reader_user_ids = await ChatRepository(db).list_reader_user_ids(int(data.get("chat_id", 0)))
            notify_user_ids = {
                int(task.publisher_id or 0),
                int(task.acceptor_id or 0),
                *[int(item) for item in reader_user_ids],
            }
            await push_chat_unread_to_participants(
                db=db,
                participant_user_ids=sorted(notify_user_ids),
                task_id=task.id,
                reason="chat_read",
                chat_id=int(data.get("chat_id", 0)),
                extra={
                    "reader_user_id": int(current_user.id),
                    "latest_message_id": int(data.get("latest_message_id", 0)),
                    "last_read_message_id": int(data.get("last_read_message_id", 0)),
                },
            )
    except Exception:
        # 通知推送失败不应影响已读主流程。
        pass
    return ok(data=data)
