import datetime as dt
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.waitlist import WaitlistStatus
from app.schemas.resource import ResourceSummary


class WaitlistCreate(BaseModel):
    """
    Request body for joining a waitlist.
    start_time must be on the hour (matches reservation slot rules).
    """
    user_id: int
    resource_id: int
    reservation_date: dt.date
    start_time: dt.time

    @field_validator("start_time")
    @classmethod
    def must_be_on_the_hour(cls, v: dt.time) -> dt.time:
        if v.minute != 0 or v.second != 0:
            raise ValueError("start_time must be on the hour (e.g. 10:00).")
        return v

    @field_validator("reservation_date")
    @classmethod
    def must_not_be_past(cls, v: dt.date) -> dt.date:
        if v < dt.date.today():
            raise ValueError("Cannot join a waitlist for a past date.")
        return v


class WaitlistResponse(BaseModel):
    """Waitlist entry detail, including queue position context."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resource_id: int
    resource: ResourceSummary
    reservation_date: dt.date
    start_time: dt.time
    end_time: dt.time
    status: WaitlistStatus
    offer_sent_at: dt.datetime | None
    offer_expires_at: dt.datetime | None
    claimed_at: dt.datetime | None
    created_at: dt.datetime
