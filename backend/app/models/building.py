"""
Building model.

Stores building-level geofence data.
Coordinates are placeholders — swap in real ASU GPS values when ready.

Placeholder coords:
  ASU Hayden Library  : 33.4183, -111.9346
  SDFC Recreation     : 33.4255, -111.9323
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    # Geofence — placeholder values; replace with surveyed coordinates
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geofence_radius_meters: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    resources: Mapped[list["Resource"]] = relationship(back_populates="building")

    def __repr__(self) -> str:
        return f"<Building id={self.id} name={self.name!r}>"
