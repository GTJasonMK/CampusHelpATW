from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ok
from app.core.settings import get_settings
from app.schemas import EmailSendCodeRequest, EmailVerifyRequest
from app.services import verify_email_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/email/send-code")
async def send_email_code(payload: EmailSendCodeRequest) -> dict:
    settings = get_settings()
    data = {"sent": True, "expire_seconds": 300}
    if settings.app_env != "prod":
        data["dev_code"] = settings.dev_verify_code
    return ok(data=data)


@router.post("/email/verify")
async def verify_email_code(
    payload: EmailVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await verify_email_login(db, payload)
    return ok(data=data)

