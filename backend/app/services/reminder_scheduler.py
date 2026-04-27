"""
Background poller that fires three timed check-in reminder emails per
reservation:

  - check_in_window_open          → 15 min before start (window opens)
  - reservation_starting          → at start time
  - check_in_deadline_approaching → 5 min before deadline (deadline = start + 15)

Idempotency:
  Each phase sends at most once per reservation. We detect prior sends by
  looking up the EmailLog table for a row with the matching (user_id, subject)
  for that reservation. Subjects are stable per-template, so we use a small
  registry that maps phase → subject prefix.

Why a poller (not APScheduler)?
  - Zero new dependencies.
  - Survives process restart automatically — on the next tick we reconcile
    against EmailLog and catch up on anything we missed while down.
  - Tolerable granularity for this prototype (within ~30 s of the target time).
"""

from __future__ import annotations

import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.email_log import EmailLog
from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource
from app.models.user import User
from app.services.messaging_service import send_event

_AZ = ZoneInfo("America/Phoenix")
_POLL_SECONDS = 30
# Send a phase only if its target time is within this window of "now".
# Past edge: we'll fire up to 10 min late (catches brief downtime).
# Future edge: 0 — never fire early.
_FIRE_LATE_TOLERANCE = dt.timedelta(minutes=10)

# Phase → (offset from start_time, event_type)
# Negative offset = before start. The deadline phase fires at start+10 (deadline-5).
_PHASES = [
    ("window_open",          dt.timedelta(minutes=-15), "check_in_window_open"),
    ("starting",             dt.timedelta(minutes=0),   "reservation_starting"),
    ("deadline_approaching", dt.timedelta(minutes=10),  "check_in_deadline_approaching"),
]


def _start_dt_utc(reservation: Reservation) -> dt.datetime:
    """Combine reservation_date + start_time as AZ local, return UTC datetime."""
    naive = dt.datetime.combine(reservation.reservation_date, reservation.start_time)
    return naive.replace(tzinfo=_AZ).astimezone(dt.timezone.utc)


def _scan_and_send_once(db: Session, now_utc: dt.datetime) -> int:
    """One pass: send any due reminders. Returns count of emails sent."""
    candidates = (
        db.query(Reservation)
        .filter(Reservation.status == ReservationStatus.reserved)
        .all()
    )

    sent = 0
    for r in candidates:
        if r.checked_in_at is not None:
            continue

        start_utc = _start_dt_utc(r)
        for _phase, offset, event_type in _PHASES:
            target = start_utc + offset
            # Fire only when now is in [target, target + late_tolerance].
            # Anything older is stale (skipped); anything newer is future (skipped).
            if now_utc < target or now_utc > target + _FIRE_LATE_TOLERANCE:
                continue
            if _already_sent_for_phase(db, r, event_type):
                continue

            user = db.query(User).filter(User.id == r.user_id).first()
            resource = db.query(Resource).filter(Resource.id == r.resource_id).first()
            if not user or not resource:
                continue

            try:
                send_event(db, event_type, user, resource, r)
                sent += 1
            except Exception as exc:
                print(f"[reminder_scheduler] send_event failed: {exc}")

    if sent:
        db.commit()
    return sent


def _already_sent_for_phase(db: Session, reservation: Reservation, event_type: str) -> bool:
    """
    Robust idempotency: we've already sent this phase for this reservation
    if a Notification of that type exists for this user where the message
    contains both the reservation's start time AND the resource name.
    """
    from app.models.notification import Notification

    slot_time = reservation.start_time.strftime("%H:%M")
    resource = db.query(Resource).filter(Resource.id == reservation.resource_id).first()
    resource_name = resource.name if resource else ""

    matches = (
        db.query(Notification)
        .filter(
            Notification.user_id == reservation.user_id,
            Notification.notification_type == event_type,
        )
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return any(
        slot_time in (m.message or "") and resource_name in (m.message or "")
        for m in matches
    )


async def _poll_loop() -> None:
    """Forever loop — runs once per _POLL_SECONDS."""
    print(f"[reminder_scheduler] started (every {_POLL_SECONDS}s)")
    while True:
        try:
            db = SessionLocal()
            try:
                count = _scan_and_send_once(db, dt.datetime.now(tz=dt.timezone.utc))
                if count:
                    print(f"[reminder_scheduler] sent {count} reminder email(s)")
            finally:
                db.close()
        except Exception as exc:
            print(f"[reminder_scheduler] tick failed: {exc}")
        await asyncio.sleep(_POLL_SECONDS)


def start_in_background() -> asyncio.Task:
    """Schedule the poll loop on the running event loop. Returns the task."""
    return asyncio.create_task(_poll_loop(), name="reminder-scheduler")
