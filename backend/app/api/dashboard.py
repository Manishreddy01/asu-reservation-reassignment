import datetime as dt
from zoneinfo import ZoneInfo

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

AZ = ZoneInfo("America/Phoenix")

_UPCOMING_STATUSES = [ReservationStatus.reserved]
_ACTIVE_STATUSES = [ReservationStatus.active, ReservationStatus.reassigned]
_HISTORY_STATUSES = [
    ReservationStatus.completed,
    ReservationStatus.no_show,
    ReservationStatus.cancelled,
    ReservationStatus.released,
]
_WAITLIST_ACTIVE = [WaitlistStatus.waiting, WaitlistStatus.offered]


@router.get(
    "/{user_id}",
    response_model=DashboardResponse,
    summary="Student dashboard",
    description=(
        "Returns all data needed to render the student dashboard: "
        "active reservations, upcoming reservations, pending no-shows, "
        "waitlist queue, unread notifications, and recent history."
    ),
)
def get_dashboard(user_id: int, db: Session = Depends(get_db)) -> DashboardResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )

    today = dt.datetime.now(tz=AZ).date()
    now_utc = dt.datetime.now(tz=dt.timezone.utc)

    # Active reservations (checked in right now — today only)
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

    # Include yesterday to catch slots that wrap past midnight (test slots near 00:00 AZ).
    yesterday = today - dt.timedelta(days=1)
    upcoming_raw = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user_id,
            Reservation.status.in_(_UPCOMING_STATUSES),
            Reservation.reservation_date >= yesterday,
        )
        .order_by(Reservation.reservation_date, Reservation.start_time)
        .all()
    )

    upcoming = []
    pending_no_show = []

    def _deadline_utc(r: Reservation) -> dt.datetime:
        d = r.check_in_deadline
        if d.tzinfo is None:
            d = d.replace(tzinfo=AZ).astimezone(dt.timezone.utc)
        return d

    for r in upcoming_raw:
        dl = _deadline_utc(r)
        if dl > now_utc:
            upcoming.append(r)
        elif r.checked_in_at is None:
            pending_no_show.append(r)

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
        pending_no_show_reservations=[ReservationResponse.model_validate(r) for r in pending_no_show],
        waitlist_entries=[WaitlistResponse.model_validate(w) for w in waitlist],
        unread_notifications=[NotificationResponse.model_validate(n) for n in unread],
        recent_history=[ReservationResponse.model_validate(r) for r in history],
    )
