"""
User model.

Roles:
  student — default for all prototype accounts
  admin   — reserved for future admin/demo panel access
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import String, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), default=UserRole.student, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships (back-populated from child tables)
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="user")
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    check_in_logs: Mapped[list["CheckInLog"]] = relationship(back_populates="user")
    email_logs: Mapped[list["EmailLog"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
