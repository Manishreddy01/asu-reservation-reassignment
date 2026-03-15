import datetime as dt
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.reservation import ReservationStatus
from app.schemas.resource import ResourceSummary


class ReservationCreate(BaseModel):
    """
    Request body for creating a new reservation.

    Prototype rules enforced here:
    - start_time must be on the hour (fixed 1-hour slots)
    - reservation_date must not be in the past
    """
    user_id: int
    resource_id: int
    reservation_date: dt.date
    start_time: dt.time

    @field_validator("start_time")
    @classmethod
    def must_be_on_the_hour(cls, v: dt.time) -> dt.time:
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
    created_at: dt.datetime
