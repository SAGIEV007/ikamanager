"""IkaManager - Ikariam Automation Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.config import get_settings
from app.routers import accounts, proxies, automation, websocket


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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts.router)
app.include_router(proxies.router)
app.include_router(automation.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
    }


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
