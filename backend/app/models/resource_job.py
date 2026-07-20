from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from datetime import datetime, timezone

from app.database import Base


class ResourceJob(Base):
    """Persisted recurring resource task (donation or building upgrade).

    One row per (account_id, kind). ``is_active`` stays True while the job
    should keep running so it can be resumed automatically after the app
    restarts. It is set to False when the user stops it or it finishes.
    """

    __tablename__ = "resource_jobs"
    __table_args__ = (UniqueConstraint("account_id", "kind", name="uq_resource_job"),)

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("ikariam_accounts.id"), nullable=False)
    kind = Column(String, nullable=False)  # "donate" | "upgrade"
    config = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
