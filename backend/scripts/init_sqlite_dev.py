#!/usr/bin/env python3
"""初始化 SQLite 本地调试库（建表 + 最小联调种子数据）。"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import bcrypt
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.database import Base, SessionLocal, engine
from app.core.settings import get_settings
from app.db_models import (
    AdminRole,
    AdminUserRole,
    Post,
    PostComment,
    PostLike,
    SystemConfig,
    Task,
    TaskCategory,
    TaskStatusLog,
    User,
)

DEMO_PASSWORD_PLAIN = "ChangeMe123!"

DEMO_USERS = [
    {
        "campus_email": "admin@campus.local",
        "nickname": "系统管理员",
        "school_name": "CampusHelpATW",
        "college_name": "平台运营",
        "reputation_score": 100,
        "help_points_balance": 1000,
        "honor_points_balance": 1000,
    },
    {
        "campus_email": "alice@campus.local",
        "nickname": "Alice",
        "school_name": "CampusHelpATW",
        "college_name": "计算机学院",
        "reputation_score": 10,
        "help_points_balance": 20,
        "honor_points_balance": 5,
    },
    {
        "campus_email": "bob@campus.local",
        "nickname": "Bob",
        "school_name": "CampusHelpATW",
        "college_name": "信息工程学院",
        "reputation_score": 8,
        "help_points_balance": 15,
        "honor_points_balance": 4,
    },
    {
        "campus_email": "charlie@campus.local",
        "nickname": "Charlie",
        "school_name": "CampusHelpATW",
        "college_name": "数学学院",
        "reputation_score": 6,
        "help_points_balance": 12,
        "honor_points_balance": 3,
    },
    {
        "campus_email": "diana@campus.local",
        "nickname": "Diana",
        "school_name": "CampusHelpATW",
        "college_name": "外语学院",
        "reputation_score": 7,
        "help_points_balance": 18,
        "honor_points_balance": 4,
    },
]

DEMO_CATEGORIES = [
    ("ERRAND", "跑腿代办", 10, True),
    ("STUDY", "学习辅导", 20, True),
    ("LIFE", "生活互助", 30, True),
    ("DOC", "资料代取", 40, True),
    ("OTHER", "其他", 99, True),
]

DEMO_SYSTEM_CONFIGS = [
    ("points.publish_cost", {"help_points": 1}, "发布任务消耗的帮助点"),
    (
        "points.task_complete_reward",
        {"help_points": 3, "honor_points": 2},
        "任务完成后帮助者奖励",
    ),
    ("points.publisher_confirm_reward", {"honor_points": 1}, "发布者按时确认完成奖励"),
    ("risk.daily_task_publish_limit", {"count": 5}, "单用户日发任务上限"),
    ("risk.daily_post_limit", {"count": 20}, "单用户日发帖上限"),
    (
        "school_branding",
        {
            "defaults": {
                "short_name": "中石大互助",
                "emblem_text": "油",
                "badge_text": "CUP",
                "slogan": "能源报国，互助同行",
                "accent_color": "#005f3c",
                "badge_bg_color": "#e8f5ec",
                "badge_text_color": "#103b2d",
                "pattern_type": "oil",
                "pattern_color": "#0f6a4c",
                "pattern_opacity": 0.18,
                "pattern_size": 22,
                "sticker_text": "石油特色",
                "sticker_bg_color": "#fff3cd",
                "sticker_text_color": "#2d2d2d",
                "ribbon_text": "中国石油大学",
                "ui_tokens": {
                    "paper_bg": "#f6fbf7",
                    "paper_dot": "#d7e7dc",
                    "ink": "#1f2f28",
                    "card_bg": "#ffffff",
                    "postit_bg": "#e8f5ec",
                    "accent_bg": "#0f6a4c",
                    "secondary_bg": "#dcece1",
                    "secondary_text": "#1f2f28",
                    "status_open_bg": "#eef8f0",
                    "status_processing_bg": "#dceee3",
                    "status_done_bg": "#d6f0df",
                    "status_danger_bg": "#ffd9d9",
                    "muted_text": "#4f5d56",
                    "sub_title_text": "#304238",
                    "error_text": "#c43d3d",
                },
            },
            "schools": [
                {
                    "school_name": "中国石油大学",
                    "short_name": "中石大",
                    "emblem_text": "油",
                    "badge_text": "CUP",
                    "slogan": "能源报国，互助同行",
                    "accent_color": "#005f3c",
                    "badge_bg_color": "#e8f5ec",
                    "badge_text_color": "#103b2d",
                    "pattern_type": "oil",
                    "pattern_color": "#0f6a4c",
                    "pattern_opacity": 0.18,
                    "pattern_size": 22,
                    "sticker_text": "石油特色",
                    "sticker_bg_color": "#fff3cd",
                    "sticker_text_color": "#2d2d2d",
                    "ribbon_text": "中国石油大学",
                },
                {
                    "school_name": "中国石油大学（华东）",
                    "short_name": "中石大华东",
                    "emblem_text": "油",
                    "badge_text": "CUP-EAST",
                    "slogan": "立足能源，服务同学",
                    "accent_color": "#006a43",
                    "badge_bg_color": "#e8f5ec",
                    "badge_text_color": "#103b2d",
                    "pattern_type": "diagonal",
                    "pattern_color": "#0b7b50",
                    "pattern_opacity": 0.2,
                    "pattern_size": 20,
                    "sticker_text": "华东校区",
                    "sticker_bg_color": "#fff1b8",
                    "sticker_text_color": "#2d2d2d",
                    "ribbon_text": "中国石油大学（华东）",
                },
                {
                    "school_name": "中国石油大学(华东)",
                    "short_name": "中石大华东",
                    "emblem_text": "油",
                    "badge_text": "CUP-EAST",
                    "slogan": "立足能源，服务同学",
                    "accent_color": "#006a43",
                    "badge_bg_color": "#e8f5ec",
                    "badge_text_color": "#103b2d",
                    "pattern_type": "diagonal",
                    "pattern_color": "#0b7b50",
                    "pattern_opacity": 0.2,
                    "pattern_size": 20,
                    "sticker_text": "华东校区",
                    "sticker_bg_color": "#fff1b8",
                    "sticker_text_color": "#2d2d2d",
                    "ribbon_text": "中国石油大学（华东）",
                },
                {
                    "school_name": "中国石油大学（北京）",
                    "short_name": "中石大北京",
                    "emblem_text": "油",
                    "badge_text": "CUP-BJ",
                    "slogan": "求实创新，互助有温度",
                    "accent_color": "#0a7a4b",
                    "badge_bg_color": "#e7f4ed",
                    "badge_text_color": "#103b2d",
                    "pattern_type": "grid",
                    "pattern_color": "#0d7449",
                    "pattern_opacity": 0.16,
                    "pattern_size": 18,
                    "sticker_text": "北京校区",
                    "sticker_bg_color": "#ffe7ba",
                    "sticker_text_color": "#2d2d2d",
                    "ribbon_text": "中国石油大学（北京）",
                },
                {
                    "school_name": "中国石油大学(北京)",
                    "short_name": "中石大北京",
                    "emblem_text": "油",
                    "badge_text": "CUP-BJ",
                    "slogan": "求实创新，互助有温度",
                    "accent_color": "#0a7a4b",
                    "badge_bg_color": "#e7f4ed",
                    "badge_text_color": "#103b2d",
                    "pattern_type": "grid",
                    "pattern_color": "#0d7449",
                    "pattern_opacity": 0.16,
                    "pattern_size": 18,
                    "sticker_text": "北京校区",
                    "sticker_bg_color": "#ffe7ba",
                    "sticker_text_color": "#2d2d2d",
                    "ribbon_text": "中国石油大学（北京）",
                },
                {
                    "school_name": "CampusHelpATW",
                    "short_name": "中石大预览",
                    "emblem_text": "油",
                    "badge_text": "CUP-Preview",
                    "slogan": "中国石油大学主题预览",
                    "accent_color": "#005f3c",
                    "badge_bg_color": "#e8f5ec",
                    "badge_text_color": "#103b2d",
                    "pattern_type": "oil",
                    "pattern_color": "#0f6a4c",
                    "pattern_opacity": 0.18,
                    "pattern_size": 22,
                    "sticker_text": "石油特色",
                    "sticker_bg_color": "#fff3cd",
                    "sticker_text_color": "#2d2d2d",
                    "ribbon_text": "中国石油大学",
                }
            ],
        },
        "学校专属样式配置（任务/事务/我的页面标识位）",
    ),
]

DEMO_POSTS = [
    {
        "title": "夜间自习室求推荐",
        "content": "晚上 10 点后还有空位的自习室有哪些？",
        "category": "HELP",
        "author_email": "alice@campus.local",
    },
    {
        "title": "任务委托避坑经验分享",
        "content": "接单前先确认截止时间和交付标准，减少后续争议。",
        "category": "SHARE",
        "author_email": "bob@campus.local",
    },
]


def _sqlite_file_path() -> Path | None:
    settings = get_settings()
    url = make_url(settings.database_url)
    if url.drivername != "sqlite+aiosqlite":
        raise RuntimeError(
            f"DATABASE_URL 必须是 sqlite+aiosqlite://...，当前为: {settings.database_url}"
        )
    if url.database in {None, "", ":memory:"}:
        return None
    return Path(url.database).resolve()


async def _upsert_user(db, payload: dict, password_hash: str) -> User:
    stmt = select(User).where(User.campus_email == payload["campus_email"])
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            campus_email=payload["campus_email"],
            password_hash=password_hash,
            nickname=payload["nickname"],
            school_name=payload["school_name"],
            college_name=payload["college_name"],
            reputation_score=payload["reputation_score"],
            help_points_balance=payload["help_points_balance"],
            honor_points_balance=payload["honor_points_balance"],
            status="ACTIVE",
        )
        db.add(user)
        await db.flush()
        return user

    user.password_hash = password_hash
    user.nickname = payload["nickname"]
    user.school_name = payload["school_name"]
    user.college_name = payload["college_name"]
    user.reputation_score = payload["reputation_score"]
    user.help_points_balance = payload["help_points_balance"]
    user.honor_points_balance = payload["honor_points_balance"]
    user.status = "ACTIVE"
    await db.flush()
    return user


async def _upsert_admin_role(db, role_code: str, role_name: str) -> AdminRole:
    role = (await db.execute(select(AdminRole).where(AdminRole.role_code == role_code))).scalar_one_or_none()
    if role is None:
        role = AdminRole(role_code=role_code, role_name=role_name)
        db.add(role)
    else:
        role.role_name = role_name
    await db.flush()
    return role


async def _ensure_admin_user_role(db, user_id: int, role_id: int) -> None:
    row = (
        await db.execute(
            select(AdminUserRole).where(
                AdminUserRole.user_id == int(user_id),
                AdminUserRole.role_id == int(role_id),
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        return
    db.add(AdminUserRole(user_id=int(user_id), role_id=int(role_id)))
    await db.flush()


async def _upsert_task_category(db, code: str, name: str, sort_order: int, is_active: bool) -> None:
    row = (await db.execute(select(TaskCategory).where(TaskCategory.code == code))).scalar_one_or_none()
    if row is None:
        row = TaskCategory(code=code, name=name, sort_order=sort_order, is_active=bool(is_active))
        db.add(row)
    else:
        row.name = name
        row.sort_order = int(sort_order)
        row.is_active = bool(is_active)
    await db.flush()


async def _upsert_system_config(db, config_key: str, config_value, description: str) -> None:
    row = (
        await db.execute(select(SystemConfig).where(SystemConfig.config_key == config_key))
    ).scalar_one_or_none()
    if row is None:
        row = SystemConfig(config_key=config_key, config_value=config_value, description=description)
        db.add(row)
    else:
        row.config_value = config_value
        row.description = description
    await db.flush()


async def _ensure_sqlite_post_columns() -> None:
    async with engine.begin() as conn:
        post_table_exists = (
            await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"),
            )
        ).first()
        if post_table_exists is None:
            return

        columns_raw = (await conn.execute(text("PRAGMA table_info(posts)"))).fetchall()
        column_names = {str(item[1]).strip().lower() for item in columns_raw if len(item) >= 2}
        if "category" not in column_names:
            await conn.execute(
                text("ALTER TABLE posts ADD COLUMN category VARCHAR(16) NOT NULL DEFAULT 'HELP'"),
            )
        if "view_count" not in column_names:
            await conn.execute(
                text("ALTER TABLE posts ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0"),
            )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_posts_status_category_created_at "
                "ON posts(status, category, created_at)"
            ),
        )


async def _ensure_demo_post(
    db,
    *,
    title: str,
    content: str,
    category: str,
    author_id: int,
) -> Post:
    row = (await db.execute(select(Post).where(Post.title == title))).scalar_one_or_none()
    if row is None:
        row = Post(
            author_id=int(author_id),
            category=str(category or "HELP").upper(),
            title=title,
            content=content,
            status="NORMAL",
        )
        db.add(row)
        await db.flush()
    return row


async def _ensure_demo_post_comment(db, *, post_id: int, author_id: int, content: str) -> None:
    exists = (
        await db.execute(
            select(PostComment).where(
                PostComment.post_id == int(post_id),
                PostComment.author_id == int(author_id),
                PostComment.content == content,
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        return
    db.add(
        PostComment(
            post_id=int(post_id),
            author_id=int(author_id),
            content=content,
        )
    )
    post = (await db.execute(select(Post).where(Post.id == int(post_id)))).scalar_one_or_none()
    if post is not None:
        post.comment_count = max(0, int(post.comment_count or 0)) + 1
    await db.flush()


async def _ensure_demo_post_like(db, *, post_id: int, user_id: int) -> None:
    exists = (
        await db.execute(
            select(PostLike).where(
                PostLike.post_id == int(post_id),
                PostLike.user_id == int(user_id),
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        return
    db.add(
        PostLike(
            post_id=int(post_id),
            user_id=int(user_id),
        )
    )
    post = (await db.execute(select(Post).where(Post.id == int(post_id)))).scalar_one_or_none()
    if post is not None:
        post.like_count = max(0, int(post.like_count or 0)) + 1
    await db.flush()


async def _ensure_demo_task(
    db,
    *,
    title: str,
    publisher_id: int,
    acceptor_id: int | None,
    status: str,
    category: str,
    description: str,
    reward_amount: Decimal,
    reward_type: str,
) -> Task:
    row = (await db.execute(select(Task).where(Task.title == title))).scalar_one_or_none()
    deadline_at = datetime.now() + timedelta(days=2)
    if row is None:
        row = Task(
            publisher_id=int(publisher_id),
            acceptor_id=int(acceptor_id) if acceptor_id else None,
            title=title,
            description=description,
            category=category,
            location_text="线上/校园内",
            reward_amount=reward_amount,
            reward_type=reward_type,
            deadline_at=deadline_at,
            status=status,
            accepted_at=datetime.now() if status in {"ACCEPTED", "IN_PROGRESS", "PENDING_CONFIRM", "DONE"} else None,
            completed_at=datetime.now() if status == "DONE" else None,
            canceled_at=datetime.now() if status == "CANCELED" else None,
        )
        db.add(row)
        await db.flush()
    return row


async def _ensure_task_log(db, task_id: int, from_status: str | None, to_status: str, operator_user_id: int) -> None:
    exists = (
        await db.execute(
            select(TaskStatusLog).where(
                TaskStatusLog.task_id == int(task_id),
                TaskStatusLog.to_status == str(to_status),
            )
        )
    ).scalars().first()
    if exists is not None:
        return
    db.add(
        TaskStatusLog(
            task_id=int(task_id),
            from_status=from_status,
            to_status=str(to_status),
            operator_user_id=int(operator_user_id),
            reason="sqlite dev seed",
        )
    )
    await db.flush()


async def init_sqlite_dev(reset: bool) -> None:
    sqlite_file = _sqlite_file_path()
    if reset and sqlite_file is not None:
        await engine.dispose()
        if sqlite_file.exists():
            sqlite_file.unlink()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_sqlite_post_columns()

    demo_password_hash = bcrypt.hashpw(
        DEMO_PASSWORD_PLAIN.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    async with SessionLocal() as db:
        users: dict[str, User] = {}
        for payload in DEMO_USERS:
            users[payload["campus_email"]] = await _upsert_user(db, payload, demo_password_hash)

        super_admin = await _upsert_admin_role(db, "SUPER_ADMIN", "超级管理员")
        await _upsert_admin_role(db, "CONTENT_MODERATOR", "内容审核员")
        await _ensure_admin_user_role(
            db,
            user_id=int(users["admin@campus.local"].id),
            role_id=int(super_admin.id),
        )

        for code, name, sort_order, is_active in DEMO_CATEGORIES:
            await _upsert_task_category(db, code, name, sort_order, is_active)
        for config_key, config_value, description in DEMO_SYSTEM_CONFIGS:
            await _upsert_system_config(db, config_key, config_value, description)

        open_task = await _ensure_demo_task(
            db,
            title="示例任务-待接单",
            publisher_id=int(users["alice@campus.local"].id),
            acceptor_id=None,
            status="OPEN",
            category="ERRAND",
            description="帮忙代取快递",
            reward_amount=Decimal("5.00"),
            reward_type="CASH",
        )
        in_progress_task = await _ensure_demo_task(
            db,
            title="示例任务-进行中",
            publisher_id=int(users["bob@campus.local"].id),
            acceptor_id=int(users["alice@campus.local"].id),
            status="IN_PROGRESS",
            category="STUDY",
            description="高数题目讲解 30 分钟",
            reward_amount=Decimal("8.00"),
            reward_type="CASH",
        )
        done_task = await _ensure_demo_task(
            db,
            title="示例任务-已完成",
            publisher_id=int(users["alice@campus.local"].id),
            acceptor_id=int(users["diana@campus.local"].id),
            status="DONE",
            category="DOC",
            description="代取材料并送到教学楼",
            reward_amount=Decimal("6.00"),
            reward_type="CASH",
        )
        await _ensure_task_log(
            db,
            task_id=int(open_task.id),
            from_status=None,
            to_status="OPEN",
            operator_user_id=int(users["alice@campus.local"].id),
        )
        await _ensure_task_log(
            db,
            task_id=int(in_progress_task.id),
            from_status="ACCEPTED",
            to_status="IN_PROGRESS",
            operator_user_id=int(users["alice@campus.local"].id),
        )
        await _ensure_task_log(
            db,
            task_id=int(done_task.id),
            from_status="PENDING_CONFIRM",
            to_status="DONE",
            operator_user_id=int(users["alice@campus.local"].id),
        )

        seeded_posts: dict[str, Post] = {}
        for item in DEMO_POSTS:
            seeded_posts[item["title"]] = await _ensure_demo_post(
                db,
                title=item["title"],
                content=item["content"],
                category=item["category"],
                author_id=int(users[item["author_email"]].id),
            )

        study_post = seeded_posts.get("夜间自习室求推荐")
        if study_post is not None:
            await _ensure_demo_post_comment(
                db,
                post_id=int(study_post.id),
                author_id=int(users["charlie@campus.local"].id),
                content="图书馆三层 24h 自习区，晚上相对安静。",
            )
            await _ensure_demo_post_like(
                db,
                post_id=int(study_post.id),
                user_id=int(users["bob@campus.local"].id),
            )

        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化 SQLite 本地调试数据")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="删除现有 sqlite 文件后重建",
    )
    args = parser.parse_args()
    asyncio.run(init_sqlite_dev(reset=bool(args.reset)))
    sqlite_file = _sqlite_file_path()
    db_text = ":memory:" if sqlite_file is None else str(sqlite_file)
    print("SQLite 初始化完成。")
    print(f"DATABASE: {db_text}")
    print("可直接执行：uvicorn app.main:app --reload --port 3000")


if __name__ == "__main__":
    main()
