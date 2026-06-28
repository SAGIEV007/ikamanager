from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    host = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String, default="https")  # https, socks5, socks4
    username = Column(String, nullable=True)
    password_encrypted = Column(String, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_valid = Column(Boolean, default=True)
    last_check = Column(DateTime, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    fail_count = Column(Integer, default=0)

    # Metadata
    label = Column(String, nullable=True)
    country = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    accounts = relationship("IkariamAccount", back_populates="proxy")

    @property
    def url(self) -> str:
        auth = ""
        if self.username:
            auth = f"{self.username}:{self.password_encrypted}@"
        return f"{self.protocol}://{auth}{self.host}:{self.port}"
