"""
EmailLog model.

Mock email system: instead of sending real emails, the system writes a row here.
A demo panel can display these rows as a simulated inbox.

status values:
  pending — queued but not yet "sent"
  sent    — logged/delivered to mock inbox
  failed  — something prevented logging (should be rare)
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class EmailStatus(str, enum.Enum):
    pending = "pending"
    sent    = "sent"
    failed  = "failed"


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    to_address: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EmailStatus] = mapped_column(
        SAEnum(EmailStatus), default=EmailStatus.sent, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="email_logs")

    def __repr__(self) -> str:
        return f"<EmailLog id={self.id} to={self.to_address!r} subject={self.subject!r}>"
