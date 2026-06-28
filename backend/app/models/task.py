from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class AutomationTask(Base):
    __tablename__ = "automation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("ikariam_accounts.id"), nullable=False)
    account = relationship("IkariamAccount", back_populates="tasks")

    task_type = Column(String, nullable=False)  # donate, build, research, piracy, collect, trade, train, login_daily
    status = Column(String, default="pending")  # pending, running, completed, failed, paused
    schedule = Column(String, nullable=True)  # cron expression or interval
    config = Column(JSON, default=dict)  # task-specific configuration

    # Execution info
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    error_message = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
