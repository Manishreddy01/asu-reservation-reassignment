"""
CheckInLog model.

Records every check-in attempt (success or failure) for audit and demo purposes.
One reservation can have multiple attempts (student may retry before deadline).

result values:
  success          — within geofence and within time window
  outside_geofence — too far from the building
  outside_window   — attempt was outside the check-in time window
  error            — unexpected server-side error during validation
"""

from datetime import datetime, timezone
from sqlalchemy import Float, Boolean, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class CheckInLog(Base):
    __tablename__ = "check_in_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Coordinates submitted by the student's browser
    submitted_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    submitted_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Computed server-side using Haversine formula
    distance_to_building_meters: Mapped[float] = mapped_column(Float, nullable=False)

    was_within_geofence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    was_within_time_window: Mapped[bool] = mapped_column(Boolean, nullable=False)

    result: Mapped[str] = mapped_column(String(40), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    reservation: Mapped["Reservation"] = relationship(back_populates="check_in_logs")
    user: Mapped["User"] = relationship(back_populates="check_in_logs")

    def __repr__(self) -> str:
        return (
            f"<CheckInLog id={self.id} reservation={self.reservation_id} "
            f"result={self.result!r}>"
        )
