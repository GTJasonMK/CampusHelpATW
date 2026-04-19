from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.response import ok
from app.core.security import get_current_user
from app.db_models import User
from app.schemas import UserOut, UserProfileUpdateRequest
from app.services import get_user_permissions, update_profile

router = APIRouter(tags=["me"])
MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024
ALLOWED_EXT_SET = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _resolve_avatar_upload_dir() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    avatar_dir = backend_root / "uploads" / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    return avatar_dir


def _detect_image_ext(content: bytes) -> str | None:
    if content.startswith(b"\xFF\xD8\xFF"):
        return ".jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return ".gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


def _guess_avatar_ext(file: UploadFile) -> str | None:
    name_ext = Path(file.filename or "").suffix.lower()
    if name_ext in ALLOWED_EXT_SET:
        return ".jpg" if name_ext == ".jpeg" else name_ext

    content_type = str(file.content_type or "").lower().strip()
    return ALLOWED_MIME_TO_EXT.get(content_type)


def _build_public_avatar_url(request: Request, filename: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/uploads/avatars/{filename}"


def _cleanup_old_local_avatar(old_avatar_url: str | None, keep_filename: str) -> None:
    old = str(old_avatar_url or "").strip()
    if not old:
        return

    marker = "/uploads/avatars/"
    index = old.find(marker)
    if index < 0:
        return

    old_filename = old[index + len(marker) :].split("?", 1)[0].strip()
    if not old_filename or old_filename == keep_filename:
        return
    if "/" in old_filename or "\\" in old_filename:
        return

    old_file_path = _resolve_avatar_upload_dir() / old_filename
    if old_file_path.exists():
        old_file_path.unlink(missing_ok=True)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return ok(data=UserOut.model_validate(current_user).model_dump())


@router.get("/me/permissions")
async def get_me_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    permissions = await get_user_permissions(db=db, user=current_user)
    return ok(data=permissions)


@router.patch("/me/profile")
async def patch_me_profile(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await update_profile(db=db, user=current_user, payload=payload)
    return ok(data=UserOut.model_validate(user).model_dump())


@router.post("/me/avatar/upload")
async def upload_me_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    content = await file.read()
    if not content:
        raise AppError(
            code=4001,
            message="empty avatar file",
            http_status=status.HTTP_400_BAD_REQUEST,
        )
    if len(content) > MAX_AVATAR_SIZE_BYTES:
        raise AppError(
            code=4001,
            message="avatar image exceeds 2MB limit",
            http_status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    detected_ext = _detect_image_ext(content)
    guessed_ext = _guess_avatar_ext(file)
    if detected_ext is None and guessed_ext is None:
        raise AppError(
            code=4001,
            message="unsupported avatar image type",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    ext = detected_ext or guessed_ext or ".jpg"
    filename = f"user_{int(current_user.id)}_{uuid4().hex}{ext}"
    avatar_dir = _resolve_avatar_upload_dir()
    avatar_path = avatar_dir / filename
    avatar_path.write_bytes(content)
    avatar_url = _build_public_avatar_url(request, filename)

    old_avatar_url = current_user.avatar_url
    try:
        updated_user = await update_profile(
            db=db,
            user=current_user,
            payload=UserProfileUpdateRequest(avatar_url=avatar_url),
        )
    except Exception:
        avatar_path.unlink(missing_ok=True)
        raise
    _cleanup_old_local_avatar(old_avatar_url, filename)

    return ok(data=UserOut.model_validate(updated_user).model_dump())
