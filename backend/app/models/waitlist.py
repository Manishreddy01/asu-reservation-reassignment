"""
WaitlistEntry model.

One row per student per resource slot.
Position/priority is determined by created_at (FCFS).

Status lifecycle:
  waiting  → queued, no active offer yet
  offered  → system has sent a claim offer; offer_expires_at is set
  claimed  → student accepted the offer and checked in
  expired  → student did not respond within 5 minutes; offer moved on
  removed  → student removed themselves from the waitlist
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import Date, Time, DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class WaitlistStatus(str, enum.Enum):
    waiting = "waiting"
    offered = "offered"
    claimed = "claimed"
    expired = "expired"
    removed = "removed"


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    __table_args__ = (
        UniqueConstraint(
            "user_id", "resource_id", "reservation_date", "start_time",
            name="uq_waitlist_user_resource_slot"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id"), nullable=False)

    reservation_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)

    status: Mapped[WaitlistStatus] = mapped_column(
        SAEnum(WaitlistStatus), default=WaitlistStatus.waiting, nullable=False
    )

    # Set when the system sends a claim offer to this student
    offer_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # offer_sent_at + 5 minutes; scheduler checks this to cascade to next student
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set when the student successfully claims the reservation
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="waitlist_entries")
    resource: Mapped["Resource"] = relationship(back_populates="waitlist_entries")

    def __repr__(self) -> str:
        return (
            f"<WaitlistEntry id={self.id} user={self.user_id} "
            f"resource={self.resource_id} status={self.status}>"
        )
