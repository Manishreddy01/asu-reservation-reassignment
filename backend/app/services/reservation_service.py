"""
Reservation creation service.

All slot-conflict and overlap validation lives here so the route handler
stays thin.  Future blocks (no-show release, reassignment) will add more
functions to this module.
"""

import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource
from app.models.user import User
from app.schemas.reservation import ReservationCreate
from app.services.messaging_service import send_event

AZ = ZoneInfo("America/Phoenix")

# Statuses that occupy a slot (cannot double-book against these)
_OCCUPYING = [
    ReservationStatus.reserved,
    ReservationStatus.active,
    ReservationStatus.reassigned,
]


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
    # For fixed 1-hour slots: same resource + same date + same start_time = double-book.
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
    # A student cannot hold two active reservations in the same time window,
    # even across different resources.
    # With fixed 1-hour slots, same date + same start_time always overlaps.
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
    end_time = (
        dt.datetime.combine(data.reservation_date, data.start_time) + dt.timedelta(hours=1)
    ).time()

    # check_in_deadline = start_time + 15 minutes, timezone-aware (Arizona)
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
    )
    db.add(reservation)

    # ── Confirmation notification + email ───────────────────────────────────
    # Committed in the same transaction so the event is atomic with the booking.
    send_event(db, "reservation_confirmed", user, resource, reservation)

    db.commit()
    db.refresh(reservation)
    return reservation
