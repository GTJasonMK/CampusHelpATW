from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ok
from app.core.security import get_current_user
from app.db_models import User
from app.schemas import ReportCreateRequest
from app.services import create_report, list_my_reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
async def create_report_endpoint(
    payload: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    report = await create_report(db=db, reporter=current_user, payload=payload)
    return ok(
        data={
            "id": report.id,
            "reporter_id": report.reporter_id,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "reason_code": report.reason_code,
            "reason_text": report.reason_text,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
    )


@router.get("/mine")
async def list_my_reports_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    data = await list_my_reports(
        db=db,
        reporter_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    data["list"] = [
        {
            "id": item.id,
            "reporter_id": item.reporter_id,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "reason_code": item.reason_code,
            "reason_text": item.reason_text,
            "status": item.status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "handled_at": item.handled_at.isoformat() if item.handled_at else None,
        }
        for item in data["list"]
    ]
    return ok(data=data)

