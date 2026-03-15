"""
Resource model.

Represents a bookable room or court within a building.

resource_type values:
  study_room        — library study rooms
  recreation_court  — SDFC recreation courts (badminton, etc.)
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ResourceType(str, enum.Enum):
    study_room = "study_room"
    recreation_court = "recreation_court"


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)

    resource_type: Mapped[ResourceType] = mapped_column(SAEnum(ResourceType), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Free-text field for equipment / room features (e.g., "Whiteboard, TV screen")
    features: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    building: Mapped["Building"] = relationship(back_populates="resources")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="resource")
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="resource")

    def __repr__(self) -> str:
        return f"<Resource id={self.id} name={self.name!r} type={self.resource_type}>"
