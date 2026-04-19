from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.core.security import parse_access_token
from app.repositories.chat_repository import ChatRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.services import (
    can_user_access_task_chat,
    create_chat_message,
    get_task_chat,
    get_transaction_channel_state,
)
from app.ws.manager import task_chat_ws_manager, user_notification_ws_manager
from app.ws.notifier import (
    build_unread_snapshot_payload,
    push_chat_unread_to_participants,
)

router = APIRouter(tags=["ws"])


@router.websocket("/ws/tasks/{task_id}")
async def task_chat_websocket(websocket: WebSocket, task_id: int) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="missing token")
        return

    try:
        user_id = parse_access_token(token)
    except AppError:
        await websocket.close(code=4401, reason="invalid token")
        return

    async with SessionLocal() as db:
        user_repo = UserRepository(db)
        task_repo = TaskRepository(db)
        user = await user_repo.get_by_id(user_id)
        task = await task_repo.get_by_id(task_id)

        if user is None:
            await websocket.close(code=4404, reason="user not found")
            return
        if task is None:
            await websocket.close(code=4404, reason="task not found")
            return
        if not can_user_access_task_chat(task, user.id):
            await websocket.close(code=4403, reason="forbidden")
            return
        channel_state = get_transaction_channel_state(task)
        if not bool(channel_state["channel_open"]):
            reason = (
                "transaction channel archived"
                if bool(channel_state["channel_archived"])
                else "transaction channel not opened yet"
            )
            await websocket.close(code=4409, reason=reason)
            return

        chat = await get_task_chat(db, task_id=task.id, operator=user)

        await task_chat_ws_manager.connect(task_id=task.id, user_id=user.id, websocket=websocket)
        await task_chat_ws_manager.broadcast(
            task.id,
            {
                "event": "join",
                "task_id": task.id,
                "chat_id": chat.id,
                "user_id": user.id,
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        )

        try:
            while True:
                data = await websocket.receive_json()
                message_type = str(data.get("message_type", "TEXT")).upper()

                if message_type == "PING":
                    await websocket.send_json(
                        {
                            "event": "pong",
                            "task_id": task.id,
                            "chat_id": chat.id,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    continue

                content = str(data.get("content", "")).strip()
                if not content:
                    await websocket.send_json({"event": "error", "message": "content required"})
                    continue

                try:
                    msg = await create_chat_message(
                        db=db,
                        chat_id=chat.id,
                        sender=user,
                        message_type=message_type,
                        content=content,
                    )
                except AppError as exc:
                    await websocket.send_json({"event": "error", "message": exc.message, "code": exc.code})
                    continue

                await task_chat_ws_manager.broadcast(
                    task.id,
                    {
                        "event": "message",
                        "task_id": task.id,
                        "chat_id": msg.chat_id,
                        "id": msg.id,
                        "sender_id": msg.sender_id,
                        "message_type": msg.message_type,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    },
                )
                try:
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
                        reason="message_created",
                        chat_id=chat.id,
                        extra={
                            "sender_id": int(msg.sender_id),
                            "message_id": int(msg.id),
                        },
                    )
                except Exception:
                    # 通知推送失败不应影响消息主流程。
                    pass
        except WebSocketDisconnect:
            task_chat_ws_manager.disconnect(task.id, websocket)
            await task_chat_ws_manager.broadcast(
                task.id,
                {
                    "event": "leave",
                    "task_id": task.id,
                    "chat_id": chat.id,
                    "user_id": user.id,
                    "ts": datetime.now(timezone.utc).isoformat(),
                },
            )


@router.websocket("/ws/me/notifications")
async def my_notification_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="missing token")
        return

    try:
        user_id = parse_access_token(token)
    except AppError:
        await websocket.close(code=4401, reason="invalid token")
        return

    async with SessionLocal() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if user is None:
            await websocket.close(code=4404, reason="user not found")
            return

        await user_notification_ws_manager.connect(user_id=user.id, websocket=websocket)
        try:
            initial_payload = await build_unread_snapshot_payload(
                db=db,
                user_id=user.id,
                reason="connect",
            )
            await websocket.send_json(initial_payload)

            while True:
                data = await websocket.receive_json()
                message_type = str(data.get("message_type", "PING")).upper()
                if message_type == "PING":
                    await websocket.send_json(
                        {
                            "event": "pong",
                            "user_id": int(user.id),
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    continue
                if message_type in {"SYNC", "SYNC_UNREAD", "SYNC_ALL"}:
                    payload = await build_unread_snapshot_payload(
                        db=db,
                        user_id=user.id,
                        reason="manual_sync",
                    )
                    await websocket.send_json(payload)
                    continue
                await websocket.send_json({"event": "error", "message": "unsupported message_type"})
        except WebSocketDisconnect:
            user_notification_ws_manager.disconnect(user.id, websocket)
