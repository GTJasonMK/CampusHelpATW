from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ok
from app.services import (
    get_meta_school_branding,
    get_meta_trust_level_rules,
    list_meta_task_categories,
)

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/task-categories")
async def list_meta_task_categories_endpoint(
    db: AsyncSession = Depends(get_db),
) -> dict:
    items = await list_meta_task_categories(db=db)
    return ok(
        data=[
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "sort_order": item.sort_order,
                "is_active": bool(item.is_active),
            }
            for item in items
        ]
    )


@router.get("/trust-level-rules")
async def get_meta_trust_level_rules_endpoint(
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await get_meta_trust_level_rules(db=db)
    return ok(data=data)


@router.get("/school-branding")
async def get_meta_school_branding_endpoint(
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await get_meta_school_branding(db=db)
    return ok(data=data)
