"""
No-show detection and release service.

Eligibility rule:
  A reservation is a no-show if ALL of the following are true:
    - status is 'reserved'
    - check_in_deadline is in the past (UTC)
    - checked_in_at is NULL

Status transition chosen:
  reserved → released  (single step)

  Rationale: the no_show event is recorded via the in-app notification
  (type='no_show') and the mock email log — these are the durable audit
  trail.  Setting status directly to 'released' keeps Block 12 simple:
  it queries released rows without needing to handle a transient no_show
  state.  'no_show' as a status is preserved in the schema for manual/seed
  scenarios where the intermediate state matters.

Duplicate-processing safety:
  The eligibility query filters status == 'reserved', so any reservation
  already transitioned to 'released' is invisible to subsequent runs.
  Calling the endpoint multiple times is therefore idempotent.

Resilience:
  If a reservation row is missing its user or resource reference (data
  integrity problem), that row is skipped and processing continues for
  the rest of the batch.  Skipped rows are not counted as processed.
"""

import datetime as dt
from sqlalchemy.orm import Session

from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource
from app.models.user import User
from app.schemas.no_show import NoShowProcessResponse, NoShowResult
from app.services.messaging_service import send_event


def process_no_shows(db: Session) -> NoShowProcessResponse:
    """
    Find all expired-unattended reservations, release them, and notify
    the affected students.

    Returns a summary of what was processed.
    """
    now = dt.datetime.now(tz=dt.timezone.utc)

    # Fetch status and null-check in SQL (safe string comparisons).
    # The deadline filter is applied in Python: SQLite stores datetimes as
    # strings, and check_in_deadline is in Arizona offset (-07:00) while now
    # is UTC (+00:00) — a raw SQL string comparison across different offsets
    # produces wrong results.  Python datetime comparison normalises both
    # values to UTC first, so it is always correct.
    candidates: list[Reservation] = (
        db.query(Reservation)
        .filter(
            Reservation.status == ReservationStatus.reserved,
            Reservation.checked_in_at.is_(None),
        )
        .all()
    )

    eligible = [r for r in candidates if r.check_in_deadline < now]

    processed: list[NoShowResult] = []

    for reservation in eligible:
        # ── Guard: skip rows with broken references ──────────────────────────
        user = db.query(User).filter(User.id == reservation.user_id).first()
        resource = db.query(Resource).filter(Resource.id == reservation.resource_id).first()
        if not user or not resource:
            continue  # data integrity problem — skip silently, do not break batch

        # ── Status transition: reserved → released ───────────────────────────
        reservation.status = ReservationStatus.released
        db.add(reservation)

        # ── Notification + email via centralized messaging service ───────────
        send_event(db, "no_show", user, resource, reservation)

        processed.append(
            NoShowResult(
                reservation_id=reservation.id,
                user_id=user.id,
                resource_name=resource.name,
                reservation_date=reservation.reservation_date,
                start_time=reservation.start_time,
            )
        )

    db.commit()

    return NoShowProcessResponse(
        reservations_checked=len(eligible),
        reservations_processed=len(processed),
        processed=processed,
    )
