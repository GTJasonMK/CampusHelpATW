from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campus_email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    school_name: Mapped[str | None] = mapped_column(String(128))
    college_name: Mapped[str | None] = mapped_column(String(128))
    reputation_score: Mapped[int] = mapped_column(default=0, nullable=False)
    help_points_balance: Mapped[int] = mapped_column(default=0, nullable=False)
    honor_points_balance: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("idx_tasks_status_category_created_at", "status", "category", "created_at"),
        Index("idx_tasks_publisher_created_at", "publisher_id", "created_at"),
        Index("idx_tasks_acceptor_created_at", "acceptor_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    acceptor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    location_text: Mapped[str | None] = mapped_column(String(255))
    reward_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=Decimal("0.00"), nullable=False)
    reward_type: Mapped[str] = mapped_column(String(16), default="NONE", nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TaskStatusLog(Base):
    __tablename__ = "task_status_logs"
    __table_args__ = (Index("idx_task_status_logs_task_created_at", "task_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class TaskChat(Base):
    __tablename__ = "task_chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class TaskChatReadCursor(Base):
    __tablename__ = "task_chat_read_cursors"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uk_task_chat_read_cursors_chat_user"),
        Index("idx_task_chat_read_cursors_user_updated_at", "user_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("task_chats.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    last_read_message_id: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("idx_chat_messages_chat_created_at", "chat_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("task_chats.id"), nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), default="TEXT", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class TaskReview(Base):
    __tablename__ = "task_reviews"
    __table_args__ = (
        UniqueConstraint("task_id", "reviewer_id", name="uk_task_reviews_task_reviewer"),
        Index("idx_task_reviews_reviewee_created_at", "reviewee_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reviewee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class PointLedger(Base):
    __tablename__ = "point_ledger"
    __table_args__ = (
        Index("idx_point_ledger_user_type_created_at", "user_id", "point_type", "created_at"),
        Index("idx_point_ledger_biz", "biz_type", "biz_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    point_type: Mapped[str] = mapped_column(String(16), nullable=False)
    change_amount: Mapped[int] = mapped_column(nullable=False)
    balance_after: Mapped[int] = mapped_column(nullable=False)
    biz_type: Mapped[str] = mapped_column(String(32), nullable=False)
    biz_id: Mapped[int | None] = mapped_column()
    remark: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("idx_posts_author_created_at", "author_id", "created_at"),
        Index("idx_posts_status_created_at", "status", "created_at"),
        Index("idx_posts_status_category_created_at", "status", "category", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(16), default="HELP", nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="NORMAL", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PostComment(Base):
    __tablename__ = "post_comments"
    __table_args__ = (Index("idx_post_comments_post_created_at", "post_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uk_post_likes_post_user"),
        Index("idx_post_likes_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class TaskCategory(Base):
    __tablename__ = "task_categories"
    __table_args__ = (
        UniqueConstraint("code", name="uk_task_categories_code"),
        Index("idx_task_categories_active_sort", "is_active", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )


class SystemConfig(Base):
    __tablename__ = "system_configs"
    __table_args__ = (UniqueConstraint("config_key", name="uk_system_configs_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    config_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_reports_target", "target_type", "target_id"),
        Index("idx_reports_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[int] = mapped_column(nullable=False)
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_text: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    handler_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    handle_result: Mapped[str | None] = mapped_column(String(500))
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class AdminOperationLog(Base):
    __tablename__ = "admin_operation_logs"
    __table_args__ = (
        Index("idx_admin_logs_admin_created_at", "admin_user_id", "created_at"),
        Index("idx_admin_logs_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[int] = mapped_column(nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


class AdminRole(Base):
    __tablename__ = "admin_roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)


class AdminUserRole(Base):
    __tablename__ = "admin_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uk_admin_user_roles_user_role"),
        Index("idx_admin_user_roles_role", "role_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("admin_roles.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )
