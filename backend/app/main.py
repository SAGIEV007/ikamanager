"""IkaManager - Ikariam Automation Platform."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.config import get_settings
from app.routers import accounts, proxies, automation, websocket, settings as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Ikariam Automation Platform - Manage multiple accounts with proxy support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(accounts.router)
app.include_router(proxies.router)
app.include_router(automation.router)
app.include_router(websocket.router)
app.include_router(settings_router.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/stats")
async def get_stats():
    """Get general platform statistics."""
    from sqlalchemy import select, func
    from app.database import async_session
    from app.models.account import IkariamAccount
    from app.models.proxy import Proxy
    from app.models.task import AutomationTask

    async with async_session() as db:
        accounts_count = await db.execute(select(func.count(IkariamAccount.id)))
        online_count = await db.execute(
            select(func.count(IkariamAccount.id)).where(IkariamAccount.is_online == True)
        )
        proxies_count = await db.execute(select(func.count(Proxy.id)))
        tasks_count = await db.execute(
            select(func.count(AutomationTask.id)).where(AutomationTask.is_active == True)
        )

    return {
        "total_accounts": accounts_count.scalar() or 0,
        "online_accounts": online_count.scalar() or 0,
        "total_proxies": proxies_count.scalar() or 0,
        "active_tasks": tasks_count.scalar() or 0,
    }


# Serve frontend static files (built React app)
STATIC_DIR = Path(__file__).parent.parent / "static"

if STATIC_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    # Serve other static files (favicon, icons)
    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(str(STATIC_DIR / "favicon.svg"))

    @app.get("/icons.svg")
    async def icons():
        return FileResponse(str(STATIC_DIR / "icons.svg"))

    # SPA fallback: any non-API route serves index.html
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Don't catch API or WebSocket routes
        if full_path.startswith("api/") or full_path.startswith("ws"):
            return {"detail": "Not Found"}
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
