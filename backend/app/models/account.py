from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class IkariamAccount(Base):
    __tablename__ = "ikariam_accounts"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password_encrypted = Column(String, nullable=False)
    server_country = Column(String, nullable=False)
    server_world = Column(String, nullable=False)
    server_number = Column(Integer, nullable=True)
    server_language = Column(String, nullable=True)
    group_name = Column(String, default="Default")

    # Session data
    session_cookie = Column(String, nullable=True)
    is_online = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    last_action = Column(DateTime, nullable=True)

    # Game data cache
    gold = Column(Float, default=0)
    action_points = Column(Integer, default=0)
    population = Column(Integer, default=0)

    # Proxy
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True)
    proxy = relationship("Proxy", back_populates="accounts")

    # Cities
    cities = relationship("City", back_populates="account", cascade="all, delete-orphan")

    # Tasks
    tasks = relationship("AutomationTask", back_populates="account", cascade="all, delete-orphan")

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    status = Column(String, default="offline")  # offline, online, error, captcha
    status_message = Column(String, nullable=True)

    # Anti-ban settings per account
    delay_min = Column(Float, default=2.0)
    delay_max = Column(Float, default=6.0)
    max_requests_per_minute = Column(Integer, default=20)
    operation_start_hour = Column(Integer, default=6)
    operation_end_hour = Column(Integer, default=23)
