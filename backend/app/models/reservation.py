"""
Reservation model.

Status lifecycle:
  reserved   → student has booked; waiting for check-in window
  active     → student checked in successfully
  completed  → reservation period ended normally after check-in
  no_show    → check-in window expired without check-in
  released   → was a no-show; now freed for reassignment
  reassigned → reassigned to a waitlisted student
  cancelled  → student cancelled before the window opened

check_in_deadline:
  Set to reservation start_time + 15 minutes.
  If the student does not check in by this datetime, the job marks the
  reservation as no_show → released.
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Date, Time, DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ReservationStatus(str, enum.Enum):
    reserved   = "reserved"
    active     = "active"
    completed  = "completed"
    no_show    = "no_show"
    released   = "released"
    reassigned = "reassigned"
    cancelled  = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"

    # Prevent the same student from having two reservations with
    # the same resource/date/start_time (exact duplicate guard).
    # Overlap across different resources is validated in application logic.
    __table_args__ = (
        UniqueConstraint(
            "user_id", "resource_id", "reservation_date", "start_time",
            name="uq_user_resource_slot"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), nullable=False)

    reservation_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)

    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus), default=ReservationStatus.reserved, nullable=False
    )

    # Deadline = start_time + 15 min; stored explicitly for easy querying
    check_in_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reservations")
    resource: Mapped["Resource"] = relationship(back_populates="reservations")
    check_in_logs: Mapped[list["CheckInLog"]] = relationship(back_populates="reservation")

    def __repr__(self) -> str:
        return (
            f"<Reservation id={self.id} user={self.user_id} "
            f"resource={self.resource_id} status={self.status}>"
        )
