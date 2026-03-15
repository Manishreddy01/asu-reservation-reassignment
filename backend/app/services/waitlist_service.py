"""
Waitlist offer, expiration, and reassignment service (Block 12).

Responsibilities:
  process_offers()       — scan released reservations; send claim offers to the
                           first eligible waiting student (FCFS by created_at).
  process_expirations()  — expire overdue offers; advance the queue to the next
                           waiting student for the same released slot.
  claim_reservation()    — validate a student's claim attempt (geofence + offer
                           still active); reassign the reservation on success.

FCFS rule:
  Among waitlist entries with status == waiting for the same
  (resource_id, reservation_date, start_time), the row with the smallest
  created_at wins.  Ties are broken by id (insertion order).

One active offer per released slot:
  Before issuing a new offer, the service checks whether a non-expired offered
  entry already exists for the same slot.  If one does, no duplicate is sent.

Remaining-queue clean-up after a successful claim:
  All other waitlist entries for the same slot (resource_id, reservation_date,
  start_time) that are still in waiting or offered status are marked removed.
  This keeps the queue tidy and prevents the system from issuing further offers
  for a slot that is no longer available.
"""

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.check_in_log import CheckInLog
from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource
from app.models.user import User
from app.models.waitlist import WaitlistEntry, WaitlistStatus
from app.schemas.waitlist_process import (
    ClaimRequest,
    ClaimResponse,
    ExpirationResult,
    OfferResult,
    ProcessExpirationsResponse,
    ProcessOffersResponse,
)
from app.services.geofence import check_geofence
from app.services.messaging_service import send_event

_OFFER_WINDOW_MINUTES = 5


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_released_reservation(
    db: Session,
    resource_id: int,
    reservation_date: dt.date,
    start_time: dt.time,
) -> Reservation | None:
    """Return the first released reservation for the given slot, or None."""
    return (
        db.query(Reservation)
        .filter(
            Reservation.resource_id == resource_id,
            Reservation.reservation_date == reservation_date,
            Reservation.start_time == start_time,
            Reservation.status == ReservationStatus.released,
        )
        .first()
    )


def _next_waiting_entry(
    db: Session,
    resource_id: int,
    reservation_date: dt.date,
    start_time: dt.time,
    exclude_id: int | None = None,
) -> WaitlistEntry | None:
    """Return the oldest waiting entry for the slot, optionally skipping one id."""
    q = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.resource_id == resource_id,
            WaitlistEntry.reservation_date == reservation_date,
            WaitlistEntry.start_time == start_time,
            WaitlistEntry.status == WaitlistStatus.waiting,
        )
        .order_by(WaitlistEntry.created_at, WaitlistEntry.id)
    )
    if exclude_id is not None:
        q = q.filter(WaitlistEntry.id != exclude_id)
    return q.first()


def _active_offer_exists(
    db: Session,
    resource_id: int,
    reservation_date: dt.date,
    start_time: dt.time,
    now: dt.datetime,
) -> bool:
    """True if a non-expired offered entry already exists for the slot."""
    return (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.resource_id == resource_id,
            WaitlistEntry.reservation_date == reservation_date,
            WaitlistEntry.start_time == start_time,
            WaitlistEntry.status == WaitlistStatus.offered,
            WaitlistEntry.offer_expires_at > now,
        )
        .first()
        is not None
    )


def _issue_offer(
    db: Session,
    entry: WaitlistEntry,
    reservation: Reservation,
    resource: Resource,
    user: User,
    now: dt.datetime,
) -> OfferResult:
    """
    Transition a waitlist entry to offered, create notification + email.
    Does NOT commit — caller is responsible for the transaction.
    """
    expires_at = now + dt.timedelta(minutes=_OFFER_WINDOW_MINUTES)

    entry.status = WaitlistStatus.offered
    entry.offer_sent_at = now
    entry.offer_expires_at = expires_at
    db.add(entry)

    send_event(
        db, "waitlist_offer", user, resource, reservation,
        offer_window_minutes=_OFFER_WINDOW_MINUTES,
    )

    return OfferResult(
        waitlist_entry_id=entry.id,
        reservation_id=reservation.id,
        user_id=user.id,
        resource_name=resource.name,
        reservation_date=reservation.reservation_date,
        start_time=reservation.start_time,
        offer_expires_at=expires_at,
    )


# ── Public service functions ──────────────────────────────────────────────────

def process_offers(db: Session) -> ProcessOffersResponse:
    """
    Scan all released reservations and issue a claim offer to the first
    eligible waiting student for each slot.

    Idempotent: a slot that already has a live (non-expired) offered entry
    is skipped.  Calling this endpoint multiple times is safe.
    """
    now = dt.datetime.now(tz=dt.timezone.utc)

    released: list[Reservation] = (
        db.query(Reservation)
        .filter(Reservation.status == ReservationStatus.released)
        .all()
    )

    offers_generated: list[OfferResult] = []

    for reservation in released:
        resource = db.query(Resource).filter(Resource.id == reservation.resource_id).first()
        if not resource:
            continue  # data integrity problem — skip

        # ── Duplicate-offer guard ─────────────────────────────────────────
        if _active_offer_exists(
            db,
            reservation.resource_id,
            reservation.reservation_date,
            reservation.start_time,
            now,
        ):
            continue  # live offer already outstanding for this slot

        # ── Find first eligible waiting entry (FCFS) ──────────────────────
        entry = _next_waiting_entry(
            db,
            reservation.resource_id,
            reservation.reservation_date,
            reservation.start_time,
        )
        if not entry:
            continue  # no one is waiting for this slot

        user = db.query(User).filter(User.id == entry.user_id).first()
        if not user:
            continue  # data integrity problem — skip

        result = _issue_offer(db, entry, reservation, resource, user, now)
        offers_generated.append(result)

    db.commit()

    return ProcessOffersResponse(
        released_reservations_checked=len(released),
        offers_generated=len(offers_generated),
        offers=offers_generated,
    )


def process_expirations(db: Session) -> ProcessExpirationsResponse:
    """
    Find all offered waitlist entries whose offer window has closed and
    expire them.  For each expired entry, advance the queue to the next
    waiting student (if the slot is still released and someone is waiting).
    """
    now = dt.datetime.now(tz=dt.timezone.utc)

    # Fetch all overdue offered entries.
    # Filter applied in Python for UTC consistency (same pattern as no_show_service).
    offered_candidates: list[WaitlistEntry] = (
        db.query(WaitlistEntry)
        .filter(WaitlistEntry.status == WaitlistStatus.offered)
        .all()
    )
    overdue = [e for e in offered_candidates if e.offer_expires_at is not None and e.offer_expires_at < now]

    expired_results: list[ExpirationResult] = []
    new_offer_results: list[OfferResult] = []

    for entry in overdue:
        resource = db.query(Resource).filter(Resource.id == entry.resource_id).first()
        user = db.query(User).filter(User.id == entry.user_id).first()
        if not resource or not user:
            continue  # data integrity problem — skip

        # ── Expire the entry ──────────────────────────────────────────────
        entry.status = WaitlistStatus.expired
        db.add(entry)

        expired_results.append(
            ExpirationResult(
                waitlist_entry_id=entry.id,
                user_id=user.id,
                resource_name=resource.name,
                reservation_date=entry.reservation_date,
                start_time=entry.start_time,
            )
        )

        # ── Advance the queue if the slot is still available ──────────────
        reservation = _find_released_reservation(
            db,
            entry.resource_id,
            entry.reservation_date,
            entry.start_time,
        )
        if not reservation:
            continue  # slot was claimed or no longer released

        next_entry = _next_waiting_entry(
            db,
            entry.resource_id,
            entry.reservation_date,
            entry.start_time,
            exclude_id=entry.id,
        )
        if not next_entry:
            continue  # no more students waiting

        next_user = db.query(User).filter(User.id == next_entry.user_id).first()
        if not next_user:
            continue

        new_offer = _issue_offer(db, next_entry, reservation, resource, next_user, now)
        new_offer_results.append(new_offer)

    db.commit()

    return ProcessExpirationsResponse(
        entries_expired=len(expired_results),
        new_offers_generated=len(new_offer_results),
        expired=expired_results,
        new_offers=new_offer_results,
    )


def claim_reservation(db: Session, data: ClaimRequest) -> ClaimResponse:
    """
    Validate and process a waitlist claim attempt.

    Steps:
      1. Verify waitlist entry exists and belongs to the requesting user.
      2. Verify entry status == offered.
      3. Verify offer has not expired.
      4. Find the matching released reservation for the slot.
      5. Resolve resource and building; run geofence check.
      6. On success:
           a. Mark entry claimed.
           b. Reassign reservation to the claiming student.
           c. Write CheckInLog.
           d. Create success notification + email.
           e. Mark remaining waiting/offered entries for this slot as removed.
      7. Return structured response.
    """
    now = dt.datetime.now(tz=dt.timezone.utc)

    # ── 1. Waitlist entry lookup ──────────────────────────────────────────────
    entry = (
        db.query(WaitlistEntry)
        .filter(WaitlistEntry.id == data.waitlist_entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Waitlist entry {data.waitlist_entry_id} not found.",
        )

    if entry.user_id != data.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This waitlist entry does not belong to you.",
        )

    # ── 2. Status guard ───────────────────────────────────────────────────────
    if entry.status == WaitlistStatus.claimed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already claimed this waitlist slot.",
        )
    if entry.status != WaitlistStatus.offered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This waitlist entry cannot be claimed — current status is "
                f"'{entry.status.value}'. Only offered entries can be claimed."
            ),
        )

    # ── 3. Expiry guard ───────────────────────────────────────────────────────
    if entry.offer_expires_at is None or entry.offer_expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "Your offer has expired. The slot has been passed to the next "
                "student on the waitlist."
            ),
        )

    # ── 4. Find the released reservation ─────────────────────────────────────
    reservation = _find_released_reservation(
        db,
        entry.resource_id,
        entry.reservation_date,
        entry.start_time,
    )
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No released reservation found for this slot. "
                "The slot may have already been claimed by another student."
            ),
        )

    # ── 5. Resource and building lookup ───────────────────────────────────────
    resource = db.query(Resource).filter(Resource.id == entry.resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated resource not found.",
        )

    building = db.query(Building).filter(Building.id == resource.building_id).first()
    if not building:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated building not found.",
        )

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {data.user_id} not found.",
        )

    # ── 5b. Geofence evaluation (reuses existing utility) ─────────────────────
    distance_meters, within_geofence = check_geofence(
        submitted_lat=data.submitted_latitude,
        submitted_lon=data.submitted_longitude,
        building_lat=building.latitude,
        building_lon=building.longitude,
        radius_meters=building.geofence_radius_meters,
    )

    if not within_geofence:
        # Write a failed check-in log for audit purposes, then return failure.
        log = CheckInLog(
            reservation_id=reservation.id,
            user_id=data.user_id,
            submitted_latitude=data.submitted_latitude,
            submitted_longitude=data.submitted_longitude,
            distance_to_building_meters=distance_meters,
            was_within_geofence=False,
            was_within_time_window=True,  # offer window governs time, not check-in window
            result="outside_geofence",
        )
        db.add(log)
        db.commit()

        return ClaimResponse(
            success=False,
            waitlist_entry_id=entry.id,
            reservation_id=reservation.id,
            user_id=data.user_id,
            resource_name=resource.name,
            reservation_date=reservation.reservation_date,
            start_time=reservation.start_time,
            distance_meters=distance_meters,
            geofence_radius_meters=building.geofence_radius_meters,
            result="outside_geofence",
            message=(
                f"Claim failed: you are {distance_meters:.1f} m from the building "
                f"(allowed radius: {building.geofence_radius_meters:.0f} m). "
                f"Please move closer and try again before your offer expires."
            ),
        )

    # ── 6. Successful claim ───────────────────────────────────────────────────

    # 6a. Mark waitlist entry as claimed.
    entry.status = WaitlistStatus.claimed
    entry.claimed_at = now
    db.add(entry)

    # 6b. Reassign reservation to the claiming student.
    reservation.user_id = data.user_id
    reservation.status = ReservationStatus.reassigned
    reservation.checked_in_at = now
    db.add(reservation)

    # 6c. Write CheckInLog for audit trail.
    log = CheckInLog(
        reservation_id=reservation.id,
        user_id=data.user_id,
        submitted_latitude=data.submitted_latitude,
        submitted_longitude=data.submitted_longitude,
        distance_to_building_meters=distance_meters,
        was_within_geofence=True,
        was_within_time_window=True,
        result="success",
    )
    db.add(log)

    # 6d. Success notification + email via centralized messaging service.
    send_event(db, "reassignment_success", user, resource, reservation)

    # 6e. Remove remaining active queue entries for this slot.
    #     This prevents the system from issuing further offers for a slot
    #     that is no longer available.
    remaining = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.resource_id == entry.resource_id,
            WaitlistEntry.reservation_date == entry.reservation_date,
            WaitlistEntry.start_time == entry.start_time,
            WaitlistEntry.status.in_([WaitlistStatus.waiting, WaitlistStatus.offered]),
            WaitlistEntry.id != entry.id,  # not the entry we just claimed
        )
        .all()
    )
    for other in remaining:
        other.status = WaitlistStatus.removed
        db.add(other)

    db.commit()

    return ClaimResponse(
        success=True,
        waitlist_entry_id=entry.id,
        reservation_id=reservation.id,
        user_id=data.user_id,
        resource_name=resource.name,
        reservation_date=reservation.reservation_date,
        start_time=reservation.start_time,
        distance_meters=distance_meters,
        geofence_radius_meters=building.geofence_radius_meters,
        result="success",
        message=(
            f"Reservation claimed successfully! You are {distance_meters:.1f} m "
            f"from the building. Your spot at {resource.name} is confirmed."
        ),
    )
