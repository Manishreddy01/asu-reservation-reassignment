import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.resource import Resource
from app.models.user import User
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.waitlist import WaitlistCreate, WaitlistResponse
from app.services.messaging_service import send_waitlist_event

router = APIRouter(prefix="/waitlists", tags=["Waitlist"])

AZ = ZoneInfo("America/Phoenix")

# Statuses that represent an active queue position (not resolved)
_ACTIVE_STATUSES = [WaitlistStatus.waiting, WaitlistStatus.offered]


class WaitlistCancelRequest(BaseModel):
    user_id: int


@router.get(
    "",
    response_model=list[WaitlistResponse],
    summary="List waitlist entries",
    description="Returns waitlist entries filtered by user and/or resource.",
)
def list_waitlists(
    user_id: int | None = Query(None, description="Filter by user ID"),
    resource_id: int | None = Query(None, description="Filter by resource ID"),
    db: Session = Depends(get_db),
) -> list[WaitlistEntry]:
    q = db.query(WaitlistEntry)
    if user_id is not None:
        q = q.filter(WaitlistEntry.user_id == user_id)
    if resource_id is not None:
        q = q.filter(WaitlistEntry.resource_id == resource_id)
    return q.order_by(WaitlistEntry.created_at).all()


@router.post(
    "",
    response_model=WaitlistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join waitlist",
    description=(
        "Adds a student to the waitlist for a fully-booked slot. "
        "Queue position is determined by sign-up time (first-come, first-served). "
        "Returns 409 if the student already has an active entry for this slot."
    ),
)
def join_waitlist(body: WaitlistCreate, db: Session = Depends(get_db)) -> WaitlistEntry:
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {body.user_id} not found.",
        )

    resource = (
        db.query(Resource)
        .filter(Resource.id == body.resource_id, Resource.is_active.is_(True))
        .first()
    )
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {body.resource_id} not found or is not available.",
        )

    duplicate = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.user_id == body.user_id,
            WaitlistEntry.resource_id == body.resource_id,
            WaitlistEntry.reservation_date == body.reservation_date,
            WaitlistEntry.start_time == body.start_time,
            WaitlistEntry.status.in_(_ACTIVE_STATUSES),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already on the waitlist for this slot.",
        )

    # Test slots (non-hour-aligned) are 15-minute windows; standard slots are 1 hour.
    is_test_slot = body.start_time.minute != 0 or body.start_time.second != 0
    slot_duration = dt.timedelta(minutes=15) if is_test_slot else dt.timedelta(hours=1)
    end_time = (
        dt.datetime.combine(body.reservation_date, body.start_time) + slot_duration
    ).time()

    entry = WaitlistEntry(
        user_id=body.user_id,
        resource_id=body.resource_id,
        reservation_date=body.reservation_date,
        start_time=body.start_time,
        end_time=end_time,
        status=WaitlistStatus.waiting,
        notification_email=body.notification_email,
    )

    db.add(entry)
    db.flush()  # populate entry.id before sending the confirmation
    send_waitlist_event(db, "waitlist_joined", user, resource, entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post(
    "/{entry_id}/cancel",
    response_model=WaitlistResponse,
    summary="Cancel a waitlist entry",
    description=(
        "Removes the requesting student from the waitlist. "
        "Allowed for entries with status 'waiting' or 'offered'. "
        "Sets status to 'removed'. Does not affect any confirmed reservation."
    ),
)
def cancel_waitlist_entry(
    entry_id: int,
    body: WaitlistCancelRequest,
    db: Session = Depends(get_db),
) -> WaitlistEntry:
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Waitlist entry {entry_id} not found.",
        )

    if entry.user_id != body.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This waitlist entry does not belong to you.",
        )

    if entry.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot cancel a waitlist entry with status '{entry.status.value}'. "
                "Only 'waiting' or 'offered' entries can be cancelled."
            ),
        )

    entry.status = WaitlistStatus.removed
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
