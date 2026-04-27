import datetime as dt
import os

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from app.models.reservation import ReservationStatus
from app.schemas.resource import ResourceSummary

_DEMO_MODE: bool = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")


class ReservationCreate(BaseModel):
    """
    Request body for creating a new reservation.

    Prototype rules enforced here:
    - start_time must be on the hour (fixed 1-hour slots) — unless DEMO_MODE
      is enabled, which allows arbitrary start times for test slots
    - reservation_date must not be in the past
    - notification_email is the address that receives the confirmation +
      check-in reminder emails. Required so reminders go to an inbox the
      student actually monitors.
    """
    user_id: int
    resource_id: int
    reservation_date: dt.date
    start_time: dt.time
    notification_email: EmailStr

    @field_validator("start_time")
    @classmethod
    def must_be_on_the_hour(cls, v: dt.time) -> dt.time:
        if _DEMO_MODE:
            return v  # allow arbitrary start times for test slots
        if v.minute != 0 or v.second != 0:
            raise ValueError("Reservations use fixed 1-hour slots. start_time must be on the hour (e.g. 09:00).")
        return v

    @field_validator("reservation_date")
    @classmethod
    def must_not_be_past(cls, v: dt.date) -> dt.date:
        if v < dt.date.today():
            raise ValueError("Cannot book a date in the past.")
        return v


class ReservationResponse(BaseModel):
    """Full reservation detail returned by GET and POST endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resource_id: int
    resource: ResourceSummary
    reservation_date: dt.date
    start_time: dt.time
    end_time: dt.time
    status: ReservationStatus
    check_in_deadline: dt.datetime
    checked_in_at: dt.datetime | None
    notification_email: str | None
    created_at: dt.datetime
