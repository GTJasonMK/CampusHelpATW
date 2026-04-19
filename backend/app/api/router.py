from fastapi import APIRouter

from app.api.routes import admin, auth, chats, me, meta, posts, reports, tasks, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(tasks.router)
api_router.include_router(tasks.aux_router)
api_router.include_router(chats.router)
api_router.include_router(posts.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(meta.router)
api_router.include_router(ws.router)
