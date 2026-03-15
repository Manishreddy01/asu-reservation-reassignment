"""
Notification model.

In-app notifications surfaced on the student dashboard.
Fetched by polling (no WebSockets for the prototype).

notification_type examples:
  reminder          — pre-reservation reminder (e.g., 15 min before)
  check_in_prompt   — check-in window is now open
  no_show           — reservation was marked as no-show
  waitlist_offer    — student on waitlist has been offered a released slot
  offer_expired     — student's claim offer expired
  reservation_confirmed — reservation is now active after successful check-in
  reassignment_success  — waitlist claim succeeded
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    notification_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} type={self.notification_type!r}>"
