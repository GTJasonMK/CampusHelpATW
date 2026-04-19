from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.router import api_router
from app.core.database import engine
from app.core.errors import AppError
from app.core.response import ok
from app.core.settings import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="CampusHelpATW FastAPI backend skeleton",
)

uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


async def _ensure_sqlite_post_schema_compat() -> None:
    if engine.dialect.name != "sqlite":
        return

    async with engine.begin() as conn:
        table_exists = (
            await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"),
            )
        ).first()
        if table_exists is None:
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


@app.on_event("startup")
async def startup_event() -> None:
    await _ensure_sqlite_post_schema_compat()


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.exception_handler(Exception)
async def unknown_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": 5000, "message": f"internal server error: {exc}", "data": None},
    )


@app.get("/healthz", tags=["system"])
async def healthz() -> dict:
    return ok(data={"status": "ok"})


app.include_router(api_router, prefix=settings.api_v1_prefix)
