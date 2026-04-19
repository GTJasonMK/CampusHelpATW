from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import Task, TaskReview, TaskStatusLog, User


class TaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _is_sqlite(self) -> bool:
        bind = self.db.get_bind()
        return bool(bind and bind.dialect.name == "sqlite")

    async def create(
        self,
        publisher_id: int,
        title: str,
        description: str,
        category: str,
        location_text: str | None,
        reward_amount,
        reward_type: str,
        deadline_at,
    ) -> Task:
        task = Task(
            publisher_id=publisher_id,
            title=title,
            description=description,
            category=category,
            location_text=location_text,
            reward_amount=reward_amount,
            reward_type=reward_type,
            deadline_at=deadline_at,
            status="OPEN",
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete_by_id(self, task_id: int) -> None:
        task = await self.get_by_id(task_id)
        if task is None:
            return
        await self.db.delete(task)
        await self.db.commit()

    async def update(self, task: Task, **fields) -> Task:
        for key, value in fields.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        return (await self.db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()

    async def list(
        self,
        status: str | None,
        category: str | None,
        page: int,
        page_size: int,
        keyword: str | None = None,
        publisher_id: int | None = None,
        acceptor_id: int | None = None,
        participant_id: int | None = None,
    ) -> tuple[list[Task], int]:
        where_clauses = []
        if status:
            statuses = [s.strip().upper() for s in status.split(",") if s.strip()]
            if len(statuses) == 1:
                where_clauses.append(Task.status == statuses[0])
            elif statuses:
                where_clauses.append(Task.status.in_(statuses))
        if category:
            where_clauses.append(Task.category == category)
        normalized_keyword = str(keyword or "").strip()
        if normalized_keyword:
            like_value = f"%{normalized_keyword}%"
            author_match_subquery = select(User.id).where(
                User.nickname.like(like_value),
            )
            where_clauses.append(
                or_(
                    Task.title.like(like_value),
                    Task.description.like(like_value),
                    Task.publisher_id.in_(author_match_subquery),
                )
            )
        if publisher_id is not None and int(publisher_id) > 0:
            where_clauses.append(Task.publisher_id == int(publisher_id))
        if acceptor_id is not None and int(acceptor_id) > 0:
            where_clauses.append(Task.acceptor_id == int(acceptor_id))
        if participant_id is not None and int(participant_id) > 0:
            pid = int(participant_id)
            where_clauses.append(or_(Task.publisher_id == pid, Task.acceptor_id == pid))

        stmt = select(Task).order_by(Task.created_at.desc())
        count_stmt = select(func.count(Task.id))
        if where_clauses:
            stmt = stmt.where(and_(*where_clauses))
            count_stmt = count_stmt.where(and_(*where_clauses))

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), int(total)

    async def list_status_logs(self, task_id: int) -> list[TaskStatusLog]:
        stmt = (
            select(TaskStatusLog)
            .where(TaskStatusLog.task_id == task_id)
            .order_by(TaskStatusLog.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_for_admin(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        category: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[Task], int]:
        where_clauses = []
        if status:
            statuses = [s.strip().upper() for s in status.split(",") if s.strip()]
            if len(statuses) == 1:
                where_clauses.append(Task.status == statuses[0])
            elif statuses:
                where_clauses.append(Task.status.in_(statuses))
        if category:
            where_clauses.append(Task.category == category)
        normalized_keyword = str(keyword or "").strip()
        if normalized_keyword:
            like_value = f"%{normalized_keyword}%"
            author_match_subquery = select(User.id).where(
                User.nickname.like(like_value),
            )
            where_clauses.append(
                or_(
                    Task.title.like(like_value),
                    Task.description.like(like_value),
                    Task.publisher_id.in_(author_match_subquery),
                )
            )

        count_stmt = select(func.count(Task.id))
        data_stmt = select(Task)
        if where_clauses:
            where_cond = and_(*where_clauses)
            count_stmt = count_stmt.where(where_cond)
            data_stmt = data_stmt.where(where_cond)

        data_stmt = data_stmt.order_by(Task.created_at.desc(), Task.id.desc())
        data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def set_acceptor(self, task_id: int, acceptor_id: int) -> None:
        await self.db.execute(update(Task).where(Task.id == task_id).values(acceptor_id=acceptor_id))
        await self.db.commit()

    async def transition(
        self,
        task_id: int,
        to_status: str,
        operator_user_id: int,
        reason: str,
    ) -> None:
        if self._is_sqlite():
            operator = (await self.db.execute(select(User).where(User.id == int(operator_user_id)))).scalar_one_or_none()
            if operator is None:
                raise ValueError("operator user not found")

            task = await self.get_by_id(task_id)
            if task is None:
                raise ValueError("task not found")

            from_status = str(task.status or "")
            task.status = str(to_status or "").upper()
            now = datetime.now()
            if task.status == "ACCEPTED" and task.accepted_at is None:
                task.accepted_at = now
            if task.status == "DONE" and task.completed_at is None:
                task.completed_at = now
            if task.status == "CANCELED" and task.canceled_at is None:
                task.canceled_at = now

            self.db.add(
                TaskStatusLog(
                    task_id=int(task.id),
                    from_status=from_status,
                    to_status=task.status,
                    operator_user_id=int(operator_user_id),
                    reason=reason,
                )
            )
            await self.db.commit()
            return

        await self.db.execute(
            text("CALL sp_task_transition(:task_id, :to_status, :operator_user_id, :reason)"),
            {
                "task_id": task_id,
                "to_status": to_status,
                "operator_user_id": operator_user_id,
                "reason": reason,
            },
        )
        await self.db.commit()

    async def create_review(
        self,
        task_id: int,
        reviewer_id: int,
        reviewee_id: int,
        rating: int,
        content: str | None,
    ) -> TaskReview:
        review = TaskReview(
            task_id=task_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            rating=rating,
            content=content,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def list_user_reviews(
        self,
        reviewee_id: int,
        page: int,
        page_size: int,
        rating: int | None = None,
        with_content: bool | None = None,
    ) -> tuple[list[TaskReview], int]:
        where_clauses = [TaskReview.reviewee_id == reviewee_id]
        if rating is not None:
            where_clauses.append(TaskReview.rating == int(rating))
        if with_content is True:
            where_clauses.append(TaskReview.content.isnot(None))
            where_clauses.append(TaskReview.content != "")

        where_cond = and_(*where_clauses)
        count_stmt = select(func.count(TaskReview.id)).where(where_cond)
        data_stmt = (
            select(TaskReview)
            .where(where_cond)
            .order_by(TaskReview.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def get_user_review_stats(self, reviewee_id: int) -> tuple[int, float]:
        stmt = select(
            func.count(TaskReview.id),
            func.avg(TaskReview.rating),
        ).where(TaskReview.reviewee_id == reviewee_id)
        count_raw, avg_raw = (await self.db.execute(stmt)).one()
        count_value = int(count_raw or 0)
        avg_value = float(avg_raw or 0.0)
        return count_value, avg_value

    async def count_shared_tasks_between_users(self, user_id_a: int, user_id_b: int) -> int:
        cond = or_(
            and_(Task.publisher_id == user_id_a, Task.acceptor_id == user_id_b),
            and_(Task.publisher_id == user_id_b, Task.acceptor_id == user_id_a),
        )
        stmt = select(func.count(Task.id)).where(cond)
        value = (await self.db.execute(stmt)).scalar_one()
        return int(value or 0)

    async def list_shared_tasks_between_users(
        self,
        user_id_a: int,
        user_id_b: int,
        page: int,
        page_size: int,
        status: str | None = None,
        sort: str = "latest",
    ) -> tuple[list[Task], int]:
        pair_cond = or_(
            and_(Task.publisher_id == user_id_a, Task.acceptor_id == user_id_b),
            and_(Task.publisher_id == user_id_b, Task.acceptor_id == user_id_a),
        )
        where_clauses = [pair_cond]
        normalized_status = str(status or "").strip().upper()
        if normalized_status:
            where_clauses.append(Task.status == normalized_status)

        where_cond = and_(*where_clauses)
        normalized_sort = str(sort or "latest").strip().lower()
        if normalized_sort == "deadline_asc":
            order_by_clauses = [Task.deadline_at.asc(), Task.id.desc()]
        elif normalized_sort == "reward_desc":
            order_by_clauses = [Task.reward_amount.desc(), Task.id.desc()]
        else:
            order_by_clauses = [Task.created_at.desc(), Task.id.desc()]

        count_stmt = select(func.count(Task.id)).where(where_cond)
        data_stmt = (
            select(Task)
            .where(where_cond)
            .order_by(*order_by_clauses)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)
