import datetime as dt
import os
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services.reservation_service import cancel_reservation, create_reservation

router = APIRouter(prefix="/reservations", tags=["Reservations"])

_DEMO_MODE: bool = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
_AZ = ZoneInfo("America/Phoenix")

# Test-slot blocker config: pre-book one study room + one court so a viewer
# logged in as any other student can exercise the Join-Waitlist flow.
_TEST_BLOCKER_USER_ID = 3  # Carol Nguyen
_TEST_BLOCKER_RESOURCE_IDS = [1, 5]  # Study Room A101, Badminton Court 1
_TEST_BLOCKER_SLOT_INDEX = 1  # the "+2 min" slot
_OCCUPYING_STATUSES = [
    ReservationStatus.reserved,
    ReservationStatus.active,
    ReservationStatus.reassigned,
]


class CancelRequest(BaseModel):
    user_id: int


@router.get(
    "",
    response_model=list[ReservationResponse],
    summary="List reservations",
    description="Returns reservations, optionally filtered by user_id and/or status.",
)
def list_reservations(
    user_id: int | None = Query(None, description="Filter by user ID"),
    status: ReservationStatus | None = Query(None, description="Filter by reservation status"),
    db: Session = Depends(get_db),
) -> list[Reservation]:
    q = db.query(Reservation)
    if user_id is not None:
        q = q.filter(Reservation.user_id == user_id)
    if status is not None:
        q = q.filter(Reservation.status == status)
    return q.order_by(Reservation.reservation_date, Reservation.start_time).all()


# ── Test-mode slots (must be registered before /{reservation_id}) ──────────────

@router.get(
    "/test-slots",
    summary="Near-future test time slots (DEMO_MODE only)",
    description=(
        "Returns deterministic short-interval time slots starting a few "
        "minutes from now. Used for testing reservation, check-in, no-show, "
        "and reassignment flows without waiting for real hour-aligned slots. "
        "Also idempotently seeds a 'blocker' reservation on one test slot so "
        "the Join-Waitlist flow can be exercised."
    ),
)
def get_test_slots(db: Session = Depends(get_db)):
    """
    Generate 4 test slots relative to the current time:
      - slot 0: starts RIGHT NOW (current minute — check-in window already open)
      - slot 1: starts in ~2 minutes  (immediate check-in testing; also blocker slot)
      - slot 2: starts in ~5 minutes  (upcoming reservation)
      - slot 3: starts in ~10 minutes (waitlist / no-show window)

    Each slot is 15 minutes long.  Future slots are rounded up to the
    next whole minute so times are clean.
    """
    if not _DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test slots are only available when DEMO_MODE is enabled.",
        )

    now = dt.datetime.now(tz=_AZ)
    now_slot = now.replace(second=0, microsecond=0)
    base = now_slot + dt.timedelta(minutes=1)

    entries = [
        now_slot,                                  # right now
        base + dt.timedelta(minutes=2),            # +~2 min
        base + dt.timedelta(minutes=5),            # +~5 min
        base + dt.timedelta(minutes=10),           # +~10 min
    ]

    slots = []
    for start in entries:
        end = start + dt.timedelta(minutes=15)
        start_str = start.strftime("%H:%M:%S")
        end_str = end.strftime("%H:%M:%S")
        label = start.strftime("%-I:%M %p") if os.name != "nt" else start.strftime("%#I:%M %p")
        slots.append({
            "label": f"TEST {label}",
            "value": start_str,
            "end_time": end_str,
            "is_test_slot": True,
        })

    _seed_test_blockers(db, entries)

    return slots


def _seed_test_blockers(db: Session, entries: list[dt.datetime]) -> None:
    """
    Ensure one study room and one court are pre-booked on a test slot so any
    other student sees 'Unavailable' and can test Join-Waitlist.

    Idempotent: skips any resource/slot that already has an occupying reservation.
    """
    if _TEST_BLOCKER_SLOT_INDEX >= len(entries):
        return

    blocker = db.query(User).filter(User.id == _TEST_BLOCKER_USER_ID).first()
    if not blocker:
        return

    start_dt_az = entries[_TEST_BLOCKER_SLOT_INDEX]
    reservation_date = start_dt_az.date()
    start_time = start_dt_az.time()
    end_time = (start_dt_az + dt.timedelta(minutes=15)).time()
    check_in_deadline = start_dt_az + dt.timedelta(minutes=15)

    created_any = False
    for resource_id in _TEST_BLOCKER_RESOURCE_IDS:
        existing = (
            db.query(Reservation)
            .filter(
                Reservation.resource_id == resource_id,
                Reservation.reservation_date == reservation_date,
                Reservation.start_time == start_time,
                Reservation.status.in_(_OCCUPYING_STATUSES),
            )
            .first()
        )
        if existing:
            continue

        db.add(Reservation(
            user_id=_TEST_BLOCKER_USER_ID,
            resource_id=resource_id,
            reservation_date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.reserved,
            check_in_deadline=check_in_deadline,
            checked_in_at=None,
            notification_email=blocker.email,
        ))
        created_any = True

    if created_any:
        db.commit()


@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
    summary="Get reservation detail",
)
def get_reservation(reservation_id: int, db: Session = Depends(get_db)) -> Reservation:
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {reservation_id} not found.",
        )
    return reservation


@router.post(
    "",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reservation",
    description=(
        "Creates a new reservation for a student. "
        "Validates slot availability, prevents double-booking, and prevents "
        "overlapping reservations for the same student. "
        "Returns 409 if the slot is already taken — use POST /waitlists to queue instead."
    ),
)
def create(body: ReservationCreate, db: Session = Depends(get_db)) -> Reservation:
    return create_reservation(db, body)


@router.post(
    "/{reservation_id}/cancel",
    response_model=ReservationResponse,
    summary="Cancel a reservation",
    description=(
        "Cancels an upcoming (reserved) reservation. "
        "Only the owning student may cancel, and only before the slot starts. "
        "If waitlisted students exist for the freed slot, an offer is immediately "
        "sent to the first student in queue (FCFS)."
    ),
)
def cancel(
    reservation_id: int,
    body: CancelRequest,
    db: Session = Depends(get_db),
) -> Reservation:
    return cancel_reservation(db, reservation_id, body.user_id)
