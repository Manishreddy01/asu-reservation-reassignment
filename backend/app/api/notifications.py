import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.notification import Notification
from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource
from app.models.user import User
from app.schemas.notification import NotificationReadResponse, NotificationResponse
from app.services.messaging_service import reminder_already_sent, send_event

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List notifications",
    description="Returns notifications for a user, newest first. Filter by user_id.",
)
def list_notifications(
    user_id: int | None = Query(None, description="Filter by user ID"),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    db: Session = Depends(get_db),
) -> list[Notification]:
    q = db.query(Notification)
    if user_id is not None:
        q = q.filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.created_at.desc()).all()


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
    summary="Mark notification as read",
)
def mark_as_read(notification_id: int, db: Session = Depends(get_db)) -> NotificationReadResponse:
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found.",
        )

    notification.is_read = True
    db.commit()
    return NotificationReadResponse(id=notification.id, is_read=True)


# ── Reminder generation ────────────────────────────────────────────────────────

class ReminderSummary(BaseModel):
    reservations_checked: int
    reminders_sent: int
    skipped_already_sent: int
    skipped_missing_data: int


@router.post(
    "/send-reminders",
    response_model=ReminderSummary,
    summary="Send reminders for upcoming reservations",
    description=(
        "Generates reminder notifications and mock email logs for students with "
        "reserved slots starting within the next `window_minutes` minutes. "
        "Skips reservations where a reminder was already sent recently. "
        "Useful for demo purposes — does not require a background scheduler."
    ),
)
def send_reminders(
    window_minutes: int = Query(
        60,
        ge=1,
        le=480,
        description="Look-ahead window in minutes (default 60, max 480)",
    ),
    db: Session = Depends(get_db),
) -> ReminderSummary:
    """
    Scan all 'reserved' reservations whose start time falls within the next
    `window_minutes` and send a reminder notification + email to the student,
    unless one was already sent recently (duplicate guard keyed on user +
    check_in_deadline window).

    Time comparisons use check_in_deadline (start + 15 min) to avoid raw
    SQLite string-comparison issues with mixed timezone offsets.
    """
    now = dt.datetime.now(tz=dt.timezone.utc)
    cutoff = now + dt.timedelta(minutes=window_minutes + 15)  # +15 because deadline = start + 15

    # Fetch all reserved reservations; filter start-time window in Python
    # (same pattern used by no_show_service to avoid SQLite TZ issues).
    candidates: list[Reservation] = (
        db.query(Reservation)
        .filter(Reservation.status == ReservationStatus.reserved)
        .all()
    )

    # Keep reservations whose start is in the future but within the window.
    # check_in_deadline = start + 15 min, so:
    #   start > now  ⟺  check_in_deadline > now + 15 min
    #   start < now + window_minutes  ⟺  check_in_deadline < now + window_minutes + 15 min
    in_window = [
        r for r in candidates
        if r.check_in_deadline is not None
        and r.check_in_deadline > now + dt.timedelta(minutes=15)
        and r.check_in_deadline <= cutoff
    ]

    reminders_sent = 0
    skipped_already = 0
    skipped_missing = 0

    for reservation in in_window:
        user = db.query(User).filter(User.id == reservation.user_id).first()
        resource = db.query(Resource).filter(Resource.id == reservation.resource_id).first()

        if not user or not resource:
            skipped_missing += 1
            continue

        if reminder_already_sent(db, user.id, reservation.check_in_deadline):
            skipped_already += 1
            continue

        send_event(db, "reminder", user, resource, reservation)
        reminders_sent += 1

    db.commit()

    return ReminderSummary(
        reservations_checked=len(in_window),
        reminders_sent=reminders_sent,
        skipped_already_sent=skipped_already,
        skipped_missing_data=skipped_missing,
    )
