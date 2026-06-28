"""API routes for automation tasks."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.task import AutomationTask

router = APIRouter(prefix="/api/tasks", tags=["automation"])


class TaskCreate(BaseModel):
    account_id: int
    task_type: str  # donate, build, research, piracy, collect, trade, train, login_daily
    schedule: Optional[str] = None  # cron or interval
    config: dict = {}


class TaskUpdate(BaseModel):
    schedule: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    account_id: int
    task_type: str
    status: str
    schedule: Optional[str]
    config: dict
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    run_count: int
    error_message: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    account_id: Optional[int] = None,
    task_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all automation tasks."""
    query = select(AutomationTask)
    if account_id:
        query = query.where(AutomationTask.account_id == account_id)
    if task_type:
        query = query.where(AutomationTask.task_type == task_type)
    query = query.order_by(AutomationTask.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.post("/", response_model=TaskResponse)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new automation task."""
    task = AutomationTask(
        account_id=data.account_id,
        task_type=data.task_type,
        schedule=data.schedule,
        config=data.config,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    result = await db.execute(
        select(AutomationTask).where(AutomationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a task."""
    result = await db.execute(
        select(AutomationTask).where(AutomationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return {"detail": "Task deleted"}


@router.post("/{task_id}/start")
async def start_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Start/resume a task."""
    result = await db.execute(
        select(AutomationTask).where(AutomationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "running"
    task.is_active = True
    await db.commit()
    return {"detail": "Task started"}


@router.post("/{task_id}/stop")
async def stop_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Stop/pause a task."""
    result = await db.execute(
        select(AutomationTask).where(AutomationTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "paused"
    task.is_active = False
    await db.commit()
    return {"detail": "Task stopped"}
