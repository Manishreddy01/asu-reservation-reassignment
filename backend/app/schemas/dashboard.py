from pydantic import BaseModel
from app.schemas.auth import UserOut
from app.schemas.reservation import ReservationResponse
from app.schemas.waitlist import WaitlistResponse
from app.schemas.notification import NotificationResponse


class DashboardResponse(BaseModel):
    """
    All data needed to render the student dashboard in one request.
    The frontend can destructure this into separate UI sections.
    """
    user: UserOut
    active_reservations: list[ReservationResponse]
    upcoming_reservations: list[ReservationResponse]
    waitlist_entries: list[WaitlistResponse]
    unread_notifications: list[NotificationResponse]
    recent_history: list[ReservationResponse]
