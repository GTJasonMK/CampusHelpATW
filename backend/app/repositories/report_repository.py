from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import Report


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        reporter_id: int,
        target_type: str,
        target_id: int,
        reason_code: str,
        reason_text: str | None,
    ) -> Report:
        report = Report(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason_code=reason_code,
            reason_text=reason_text,
            status="PENDING",
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_by_id(self, report_id: int) -> Report | None:
        return (await self.db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()

    async def list_by_reporter(self, reporter_id: int, page: int, page_size: int) -> tuple[list[Report], int]:
        count_stmt = select(func.count(Report.id)).where(Report.reporter_id == reporter_id)
        data_stmt = (
            select(Report)
            .where(Report.reporter_id == reporter_id)
            .order_by(Report.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def list_for_admin(
        self,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Report], int]:
        where_clauses = []
        if status:
            where_clauses.append(Report.status == status)

        count_stmt = select(func.count(Report.id))
        data_stmt = select(Report).order_by(Report.created_at.desc())
        if where_clauses:
            count_stmt = count_stmt.where(and_(*where_clauses))
            data_stmt = data_stmt.where(and_(*where_clauses))

        data_stmt = data_stmt.offset((page - 1) * page_size).limit(page_size)
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = (await self.db.execute(data_stmt)).scalars().all()
        return list(items), int(total)

    async def handle(self, report: Report, admin_id: int, action: str, result: str) -> Report:
        report.status = "RESOLVED" if action.upper() == "RESOLVE" else "REJECTED"
        report.handler_admin_id = admin_id
        report.handle_result = result
        report.handled_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(report)
        return report

