"""
Reservation creation and cancellation service.

All slot-conflict/overlap validation and cancellation logic lives here
so route handlers stay thin.
"""

import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource
from app.models.user import User
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.reservation import ReservationCreate
from app.services.messaging_service import send_event, send_waitlist_event

AZ = ZoneInfo("America/Phoenix")

# Statuses that occupy a slot (cannot double-book against these)
_OCCUPYING = [
    ReservationStatus.reserved,
    ReservationStatus.active,
    ReservationStatus.reassigned,
]

_OFFER_WINDOW_MINUTES = 5


def create_reservation(db: Session, data: ReservationCreate) -> Reservation:
    """
    Validate and create a new reservation.

    Validation order (intentional — cheapest checks first):
      1. User exists
      2. Resource exists and is active
      3. Resource not already occupied for this exact slot
      4. User has no conflicting reservation in the same time window
    """

    # ── 1. User ────────────────────────────────────────────────────────────
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {data.user_id} not found.",
        )

    # ── 2. Resource ────────────────────────────────────────────────────────
    resource = (
        db.query(Resource)
        .filter(Resource.id == data.resource_id, Resource.is_active.is_(True))
        .first()
    )
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {data.resource_id} not found or is not available.",
        )

    # ── 3. Resource slot conflict ───────────────────────────────────────────
    slot_taken = (
        db.query(Reservation)
        .filter(
            Reservation.resource_id == data.resource_id,
            Reservation.reservation_date == data.reservation_date,
            Reservation.start_time == data.start_time,
            Reservation.status.in_(_OCCUPYING),
        )
        .first()
    )
    if slot_taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This slot is already booked. "
                "Use POST /waitlists to join the waitlist for this slot."
            ),
        )

    # ── 4. User overlap conflict ────────────────────────────────────────────
    user_conflict = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == data.user_id,
            Reservation.reservation_date == data.reservation_date,
            Reservation.start_time == data.start_time,
            Reservation.status.in_(_OCCUPYING),
        )
        .first()
    )
    if user_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "You already have a reservation in this time slot. "
                "Overlapping reservations are not allowed."
            ),
        )

    # ── Compute derived fields ──────────────────────────────────────────────
    # Test slots (non-hour-aligned) use a 15-minute duration;
    # production slots use the standard 1-hour duration.
    is_test_slot = data.start_time.minute != 0 or data.start_time.second != 0
    slot_duration = dt.timedelta(minutes=15) if is_test_slot else dt.timedelta(hours=1)

    end_time = (
        dt.datetime.combine(data.reservation_date, data.start_time) + slot_duration
    ).time()

    start_dt = dt.datetime.combine(data.reservation_date, data.start_time, tzinfo=AZ)
    check_in_deadline = start_dt + dt.timedelta(minutes=15)

    # ── Create ─────────────────────────────────────────────────────────────
    reservation = Reservation(
        user_id=data.user_id,
        resource_id=data.resource_id,
        reservation_date=data.reservation_date,
        start_time=data.start_time,
        end_time=end_time,
        status=ReservationStatus.reserved,
        check_in_deadline=check_in_deadline,
        checked_in_at=None,
        notification_email=data.notification_email,
    )
    db.add(reservation)
    db.flush()  # assign reservation.id before send_event uses it

    send_event(db, "reservation_confirmed", user, resource, reservation)

    db.commit()
    db.refresh(reservation)
    return reservation


def cancel_reservation(db: Session, reservation_id: int, user_id: int) -> Reservation:
    """
    Cancel a future reservation belonging to the requesting user.

    Rules:
    - Reservation must exist and belong to user_id.
    - Status must be 'reserved' (only pre-check-in reservations are cancellable).
    - Start time must not have passed yet.

    On success:
    - Marks the reservation as 'cancelled'.
    - Sends a cancellation notification + email to the student.
    - If waitlisted students exist for this slot, issues an offer to the
      first waiting student (FCFS) so the freed slot can be claimed.
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {reservation_id} not found.",
        )

    if reservation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This reservation does not belong to you.",
        )

    if reservation.status != ReservationStatus.reserved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot cancel a reservation with status '{reservation.status.value}'. "
                "Only upcoming (reserved) reservations can be cancelled."
            ),
        )

    # Ensure start time hasn't passed
    start_dt = dt.datetime.combine(
        reservation.reservation_date, reservation.start_time, tzinfo=AZ
    )
    now_az = dt.datetime.now(tz=AZ)
    if start_dt <= now_az:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel a reservation that has already started or passed.",
        )

    resource = db.query(Resource).filter(Resource.id == reservation.resource_id).first()
    user = db.query(User).filter(User.id == user_id).first()

    # Mark cancelled
    reservation.status = ReservationStatus.cancelled
    db.add(reservation)

    # Cancellation notification to the student
    send_event(db, "cancellation_confirmed", user, resource, reservation)

    # ── Offer freed slot to first waiting student (FCFS) ───────────────────
    waiting_entry = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.resource_id == reservation.resource_id,
            WaitlistEntry.reservation_date == reservation.reservation_date,
            WaitlistEntry.start_time == reservation.start_time,
            WaitlistEntry.status == WaitlistStatus.waiting,
        )
        .order_by(WaitlistEntry.created_at, WaitlistEntry.id)
        .first()
    )

    if waiting_entry:
        waiting_user = db.query(User).filter(User.id == waiting_entry.user_id).first()
        if waiting_user:
            now_utc = dt.datetime.now(tz=dt.timezone.utc)
            offer_expires = now_utc + dt.timedelta(minutes=_OFFER_WINDOW_MINUTES)
            waiting_entry.status = WaitlistStatus.offered
            waiting_entry.offer_sent_at = now_utc
            waiting_entry.offer_expires_at = offer_expires
            db.add(waiting_entry)

            send_waitlist_event(
                db, "waitlist_offer", waiting_user, resource, waiting_entry,
                offer_window_minutes=_OFFER_WINDOW_MINUTES,
            )

    db.commit()
    db.refresh(reservation)
    return reservation
