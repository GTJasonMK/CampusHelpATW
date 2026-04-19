from datetime import datetime, timezone
from typing import Iterable

from app.repositories.chat_repository import ChatRepository
from app.ws.manager import user_notification_ws_manager


def _normalize_participants(participant_user_ids: Iterable[int | None]) -> list[int]:
    normalized: list[int] = []
    seen: set[int] = set()
    for raw_id in participant_user_ids:
        user_id = int(raw_id or 0)
        if user_id <= 0 or user_id in seen:
            continue
        seen.add(user_id)
        normalized.append(user_id)
    return normalized


async def _build_user_unread_payload(
    db,
    user_id: int,
    task_id: int,
    reason: str,
    chat_id: int | None = None,
    extra: dict | None = None,
) -> dict:
    repo = ChatRepository(db)
    unread_items = await repo.list_unread_counts_by_user(user_id)
    total_unread = sum(max(0, int(item.get("unread_count", 0))) for item in unread_items)

    task_unread = next(
        (item for item in unread_items if int(item.get("task_id", 0)) == int(task_id)),
        None,
    )
    unread_count = int(task_unread.get("unread_count", 0)) if task_unread else 0
    latest_message_id = int(task_unread.get("latest_message_id", 0)) if task_unread else 0
    last_read_message_id = int(task_unread.get("last_read_message_id", 0)) if task_unread else 0
    resolved_chat_id = int(task_unread.get("chat_id", 0)) if task_unread else int(chat_id or 0)

    payload = {
        "event": "chat_unread",
        "reason": reason,
        "user_id": int(user_id),
        "task_id": int(task_id),
        "chat_id": resolved_chat_id,
        "unread_count": unread_count,
        "total_unread": int(total_unread),
        "latest_message_id": latest_message_id,
        "last_read_message_id": last_read_message_id,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    return payload


async def push_chat_unread_to_user(
    db,
    user_id: int,
    task_id: int,
    reason: str,
    chat_id: int | None = None,
    extra: dict | None = None,
) -> None:
    payload = await _build_user_unread_payload(
        db=db,
        user_id=user_id,
        task_id=task_id,
        reason=reason,
        chat_id=chat_id,
        extra=extra,
    )
    await user_notification_ws_manager.send_to_user(user_id, payload)


async def push_chat_unread_to_participants(
    db,
    participant_user_ids: Iterable[int | None],
    task_id: int,
    reason: str,
    chat_id: int | None = None,
    extra: dict | None = None,
) -> None:
    participants = _normalize_participants(participant_user_ids)
    for user_id in participants:
        await push_chat_unread_to_user(
            db=db,
            user_id=user_id,
            task_id=task_id,
            reason=reason,
            chat_id=chat_id,
            extra=extra,
        )


async def build_unread_snapshot_payload(db, user_id: int, reason: str = "snapshot") -> dict:
    items = await ChatRepository(db).list_unread_counts_by_user(user_id)
    total_unread = sum(max(0, int(item.get("unread_count", 0))) for item in items)
    return {
        "event": "unread_snapshot",
        "reason": reason,
        "user_id": int(user_id),
        "total_unread": int(total_unread),
        "items": items,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


async def push_task_event_to_participants(
    participant_user_ids: Iterable[int | None],
    task_id: int,
    status: str,
    action: str,
    operator_user_id: int,
    reason: str | None = None,
    extra: dict | None = None,
) -> None:
    participants = _normalize_participants(participant_user_ids)
    payload = {
        "event": "task_event",
        "task_id": int(task_id),
        "status": str(status),
        "action": str(action),
        "operator_user_id": int(operator_user_id),
        "reason": reason or "",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)

    for user_id in participants:
        await user_notification_ws_manager.send_to_user(user_id, payload)
