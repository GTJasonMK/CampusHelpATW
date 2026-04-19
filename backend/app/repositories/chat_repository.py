from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import ChatMessage, Task, TaskChat, TaskChatReadCursor


class ChatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_task_id(self, task_id: int) -> TaskChat | None:
        return (await self.db.execute(select(TaskChat).where(TaskChat.task_id == task_id))).scalar_one_or_none()

    async def get_by_chat_id(self, chat_id: int) -> TaskChat | None:
        return (await self.db.execute(select(TaskChat).where(TaskChat.id == chat_id))).scalar_one_or_none()

    async def get_read_cursor(self, chat_id: int, user_id: int) -> TaskChatReadCursor | None:
        stmt = select(TaskChatReadCursor).where(
            TaskChatReadCursor.chat_id == chat_id,
            TaskChatReadCursor.user_id == user_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_reader_user_ids(self, chat_id: int) -> list[int]:
        stmt = select(TaskChatReadCursor.user_id).where(TaskChatReadCursor.chat_id == chat_id)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [int(item) for item in rows if int(item or 0) > 0]

    async def get_or_create_by_task_id(self, task_id: int) -> TaskChat:
        chat = await self.get_by_task_id(task_id)
        if chat is not None:
            return chat
        chat = TaskChat(task_id=task_id)
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def list_messages(
        self,
        chat_id: int,
        cursor: int,
        page_size: int,
    ) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id, ChatMessage.id > cursor)
            .order_by(ChatMessage.id.asc())
            .limit(page_size)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_message(
        self,
        chat_id: int,
        sender_id: int,
        message_type: str,
        content: str,
    ) -> ChatMessage:
        msg = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_latest_message_id(self, chat_id: int) -> int:
        stmt = select(func.coalesce(func.max(ChatMessage.id), 0)).where(ChatMessage.chat_id == chat_id)
        value = (await self.db.execute(stmt)).scalar_one()
        return int(value or 0)

    async def touch_read_cursor(
        self,
        chat_id: int,
        user_id: int,
        last_read_message_id: int,
    ) -> TaskChatReadCursor:
        safe_last_read = max(0, int(last_read_message_id or 0))
        cursor = await self.get_read_cursor(chat_id=chat_id, user_id=user_id)
        if cursor is None:
            cursor = TaskChatReadCursor(
                chat_id=chat_id,
                user_id=user_id,
                last_read_message_id=safe_last_read,
            )
            self.db.add(cursor)
        else:
            cursor.last_read_message_id = max(int(cursor.last_read_message_id or 0), safe_last_read)
        await self.db.commit()
        await self.db.refresh(cursor)
        return cursor

    async def list_unread_counts_by_user(self, user_id: int) -> list[dict]:
        unread_expr = func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            ChatMessage.sender_id != user_id,
                            ChatMessage.id > func.coalesce(TaskChatReadCursor.last_read_message_id, 0),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        )
        stmt = (
            select(
                TaskChat.task_id.label("task_id"),
                TaskChat.id.label("chat_id"),
                unread_expr.label("unread_count"),
                func.coalesce(func.max(ChatMessage.id), 0).label("latest_message_id"),
                func.coalesce(TaskChatReadCursor.last_read_message_id, 0).label("last_read_message_id"),
            )
            .join(Task, Task.id == TaskChat.task_id)
            .outerjoin(
                TaskChatReadCursor,
                and_(
                    TaskChatReadCursor.chat_id == TaskChat.id,
                    TaskChatReadCursor.user_id == user_id,
                ),
            )
            .outerjoin(ChatMessage, ChatMessage.chat_id == TaskChat.id)
            .where(
                or_(
                    Task.publisher_id == user_id,
                    Task.acceptor_id == user_id,
                    TaskChatReadCursor.user_id == user_id,
                )
            )
            .group_by(TaskChat.task_id, TaskChat.id, TaskChatReadCursor.last_read_message_id)
            .order_by(TaskChat.task_id.asc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "task_id": int(row.task_id),
                "chat_id": int(row.chat_id),
                "unread_count": int(row.unread_count or 0),
                "latest_message_id": int(row.latest_message_id or 0),
                "last_read_message_id": int(row.last_read_message_id or 0),
            }
            for row in rows
        ]

    async def get_unread_count_by_user_and_task(self, user_id: int, task_id: int) -> dict | None:
        unread_expr = func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            ChatMessage.sender_id != user_id,
                            ChatMessage.id > func.coalesce(TaskChatReadCursor.last_read_message_id, 0),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        )
        stmt = (
            select(
                TaskChat.task_id.label("task_id"),
                TaskChat.id.label("chat_id"),
                unread_expr.label("unread_count"),
                func.coalesce(func.max(ChatMessage.id), 0).label("latest_message_id"),
                func.coalesce(TaskChatReadCursor.last_read_message_id, 0).label("last_read_message_id"),
            )
            .join(Task, Task.id == TaskChat.task_id)
            .outerjoin(
                TaskChatReadCursor,
                and_(
                    TaskChatReadCursor.chat_id == TaskChat.id,
                    TaskChatReadCursor.user_id == user_id,
                ),
            )
            .outerjoin(ChatMessage, ChatMessage.chat_id == TaskChat.id)
            .where(
                TaskChat.task_id == task_id,
                or_(
                    Task.publisher_id == user_id,
                    Task.acceptor_id == user_id,
                    TaskChatReadCursor.user_id == user_id,
                ),
            )
            .group_by(TaskChat.task_id, TaskChat.id, TaskChatReadCursor.last_read_message_id)
            .limit(1)
        )
        row = (await self.db.execute(stmt)).first()
        if row is None:
            return None
        return {
            "task_id": int(row.task_id),
            "chat_id": int(row.chat_id),
            "unread_count": int(row.unread_count or 0),
            "latest_message_id": int(row.latest_message_id or 0),
            "last_read_message_id": int(row.last_read_message_id or 0),
        }
