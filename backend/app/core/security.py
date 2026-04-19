from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.settings import get_settings
from app.db_models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(plain_password, password_hash)
    except ValueError as exc:
        # Compatibility fallback for passlib+bcrypt runtime mismatch on some
        # environments where passlib internal probing raises this ValueError.
        if "longer than 72 bytes" not in str(exc):
            raise
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def parse_access_token(token: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if sub is None:
            raise AppError(code=4003, message="token payload invalid", http_status=401)
        return int(sub)
    except jwt.PyJWTError as exc:
        raise AppError(code=4003, message="token invalid or expired", http_status=401) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(code=4003, message="missing authorization header", http_status=401)

    user_id = parse_access_token(credentials.credentials)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(code=4003, message="user not found", http_status=401)
    if user.status != "ACTIVE":
        raise AppError(code=4003, message="user is not active", http_status=401)
    return user
