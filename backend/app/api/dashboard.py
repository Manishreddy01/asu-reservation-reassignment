import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.notification import Notification
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.auth import UserOut
from app.schemas.dashboard import DashboardResponse
from app.schemas.notification import NotificationResponse
from app.schemas.reservation import ReservationResponse
from app.schemas.waitlist import WaitlistResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_UPCOMING_STATUSES = [ReservationStatus.reserved]
_ACTIVE_STATUSES = [ReservationStatus.active, ReservationStatus.reassigned]
_HISTORY_STATUSES = [
    ReservationStatus.completed,
    ReservationStatus.no_show,
    ReservationStatus.cancelled,
]
_WAITLIST_ACTIVE = [WaitlistStatus.waiting, WaitlistStatus.offered]


@router.get(
    "/{user_id}",
    response_model=DashboardResponse,
    summary="Student dashboard",
    description=(
        "Returns all data needed to render the student dashboard: "
        "active reservations, upcoming reservations, waitlist queue, "
        "unread notifications, and recent history."
    ),
)
def get_dashboard(user_id: int, db: Session = Depends(get_db)) -> DashboardResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    today = dt.date.today()

    # Active reservations (checked in right now)
    active = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user_id,
            Reservation.status.in_(_ACTIVE_STATUSES),
            Reservation.reservation_date == today,
        )
        .order_by(Reservation.start_time)
        .all()
    )

    # Upcoming reservations (reserved but not yet checked in, today or future)
    upcoming = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user_id,
            Reservation.status.in_(_UPCOMING_STATUSES),
            Reservation.reservation_date >= today,
        )
        .order_by(Reservation.reservation_date, Reservation.start_time)
        .all()
    )

    # Active waitlist entries
    waitlist = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.status.in_(_WAITLIST_ACTIVE),
            WaitlistEntry.reservation_date >= today,
        )
        .order_by(WaitlistEntry.reservation_date, WaitlistEntry.start_time)
        .all()
    )

    # Unread notifications
    unread = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .order_by(Notification.created_at.desc())
        .all()
    )

    # Recent history — last 10 resolved reservations
    history = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user_id,
            Reservation.status.in_(_HISTORY_STATUSES),
        )
        .order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc())
        .limit(10)
        .all()
    )

    return DashboardResponse(
        user=UserOut.model_validate(user),
        active_reservations=[ReservationResponse.model_validate(r) for r in active],
        upcoming_reservations=[ReservationResponse.model_validate(r) for r in upcoming],
        waitlist_entries=[WaitlistResponse.model_validate(w) for w in waitlist],
        unread_notifications=[NotificationResponse.model_validate(n) for n in unread],
        recent_history=[ReservationResponse.model_validate(r) for r in history],
    )
