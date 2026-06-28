from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, nullable=False)  # Ikariam city ID
    account_id = Column(Integer, ForeignKey("ikariam_accounts.id"), nullable=False)
    account = relationship("IkariamAccount", back_populates="cities")

    name = Column(String, nullable=False)
    island_id = Column(Integer, nullable=True)
    island_x = Column(Integer, nullable=True)
    island_y = Column(Integer, nullable=True)
    level = Column(Integer, default=1)

    # Resources
    wood = Column(Integer, default=0)
    wine = Column(Integer, default=0)
    marble = Column(Integer, default=0)
    crystal = Column(Integer, default=0)
    sulfur = Column(Integer, default=0)
    wood_per_hour = Column(Float, default=0)
    wine_per_hour = Column(Float, default=0)
    marble_per_hour = Column(Float, default=0)
    crystal_per_hour = Column(Float, default=0)
    sulfur_per_hour = Column(Float, default=0)

    # Population
    population = Column(Integer, default=0)
    max_population = Column(Integer, default=0)
    citizens = Column(Integer, default=0)

    # Buildings (JSON with building levels)
    buildings = Column(JSON, default=dict)

    # Military
    troops = Column(JSON, default=dict)
    ships = Column(JSON, default=dict)

    # Metadata
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_capital = Column(Boolean, default=False)
