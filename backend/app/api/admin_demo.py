"""
Admin / Demo Controls — Block 14.

Provides a small set of developer/demo helper endpoints that let a presenter
trigger and inspect core flows during a live demo without touching production
logic.

All endpoints are guarded: they only respond if either
  - DEMO_MODE=true  is set in the server environment, OR
  - the request includes  X-Demo-Key: <value>  that matches the DEMO_KEY
    environment variable.
If neither condition is met, every endpoint returns HTTP 403.

To enable for local development, either:
  1. Start the server with  DEMO_MODE=true uvicorn main:app --reload
  2. Or export DEMO_KEY=<secret> and pass X-Demo-Key: <secret> in every request.

Time-offset (dt_offset_minutes):
  Several endpoints accept an optional dt_offset_minutes integer.  When set,
  the endpoint temporarily shifts the internal clock used by the underlying
  service by that many minutes (positive = forward, negative = backward).
  This lets a presenter simulate "time has passed" without changing any
  DB rows.  The shift is applied only for the duration of that single call
  via a context-manager patch on datetime.datetime — no DB rows are mutated.
"""

import datetime as dt
import logging
import os
from contextlib import contextmanager
from typing import Generator
from unittest.mock import patch

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.check_in_log import CheckInLog
from app.models.notification import Notification
from app.models.reservation import Reservation, ReservationStatus
from app.models.waitlist import WaitlistEntry
from app.schemas.no_show import NoShowProcessResponse
from app.schemas.notification import NotificationResponse
from app.schemas.reservation import ReservationResponse
from app.schemas.waitlist import WaitlistResponse
from app.schemas.waitlist_process import (
    ClaimResponse,
    ProcessExpirationsResponse,
    ProcessOffersResponse,
)
import app.services.no_show_service as _no_show_svc
import app.services.waitlist_service as _waitlist_svc
from app.api.notifications import ReminderSummary, send_reminders as _send_reminders_endpoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin-demo", tags=["Admin / Demo Controls"])

# ── Configuration ─────────────────────────────────────────────────────────────

_DEMO_MODE: bool = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
_DEMO_KEY: str = os.getenv("DEMO_KEY", "")


# ── Security guard ────────────────────────────────────────────────────────────

def _require_demo_access(x_demo_key: str | None = Header(default=None)) -> None:
    """
    FastAPI dependency.  Passes through if DEMO_MODE is enabled OR if the
    request carries a valid X-Demo-Key header.  Raises 403 otherwise.
    """
    if _DEMO_MODE:
        return
    if _DEMO_KEY and x_demo_key == _DEMO_KEY:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Demo mode is not enabled. "
            "Set DEMO_MODE=true in the server environment, "
            "or set DEMO_KEY=<secret> and pass X-Demo-Key: <secret> in every request."
        ),
    )


# ── Time-offset context manager ───────────────────────────────────────────────

@contextmanager
def _simulated_time(offset_minutes: int | None) -> Generator[None, None, None]:
    """
    Temporarily replaces datetime.datetime.now() to return
    (real UTC now + offset_minutes) for the duration of the block.

    Uses unittest.mock.patch on 'datetime.datetime' in the datetime module so
    that all service code using `import datetime as dt; dt.datetime.now(...)` sees
    the shifted time.  Does NOT touch any DB rows.

    If offset_minutes is None or 0, behaves as a no-op.
    """
    if not offset_minutes:
        yield
        return

    shifted = dt.datetime.now(tz=dt.timezone.utc) + dt.timedelta(minutes=offset_minutes)
    _real_dt = dt.datetime  # capture before patch

    class _FakeDatetime(_real_dt):
        @classmethod
        def now(cls, tz=None):
            if tz is not None:
                return shifted.astimezone(tz)
            return shifted.replace(tzinfo=None)

        @classmethod
        def utcnow(cls):
            return shifted.replace(tzinfo=None)

    # Patch datetime.datetime in the module so dt.datetime.now() is intercepted
    # in every service that uses `import datetime as dt`.
    with patch("datetime.datetime", _FakeDatetime):
        logger.info(
            "[admin-demo] Simulated time active: offset=%+d min, effective_now=%s",
            offset_minutes,
            shifted.isoformat(),
        )
        yield


# ── Inline request schemas ────────────────────────────────────────────────────

class OffsetBody(BaseModel):
    """Request body shared by endpoints that only need a time offset."""
    dt_offset_minutes: int | None = None


class ReminderDemoBody(BaseModel):
    """Request body for the send-reminders demo endpoint."""
    window_minutes: int = 60
    dt_offset_minutes: int | None = None


class ClaimDemoBody(BaseModel):
    """Request body for the claim-waitlist demo endpoint."""
    user_id: int
    waitlist_entry_id: int
    submitted_latitude: float
    submitted_longitude: float
    dt_offset_minutes: int | None = None


# ── Inspect response schemas ──────────────────────────────────────────────────

class CheckInLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reservation_id: int
    user_id: int
    submitted_latitude: float
    submitted_longitude: float
    distance_to_building_meters: float
    was_within_geofence: bool
    was_within_time_window: bool
    result: str
    created_at: dt.datetime


class InspectSnapshot(BaseModel):
    """Read-only DB snapshot returned by GET /admin-demo/inspect."""
    recent_reservations: list[ReservationResponse]
    released_reservations: list[ReservationResponse]
    recent_waitlist: list[WaitlistResponse]
    recent_notifications: list[NotificationResponse]
    recent_check_in_logs: list[CheckInLogOut]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/no-shows",
    response_model=NoShowProcessResponse,
    summary="[DEMO] Trigger no-show processing",
    description=(
        "Runs the no-show detection pass.  Reservations whose check-in deadline "
        "has passed without a check-in are transitioned to 'released' and the "
        "affected students are notified.  Pass dt_offset_minutes to simulate "
        "that time has advanced (e.g. 90 to pretend it is 90 minutes later)."
    ),
)
def demo_process_no_shows(
    body: OffsetBody = OffsetBody(),
    db: Session = Depends(get_db),
    _: None = Depends(_require_demo_access),
) -> NoShowProcessResponse:
    logger.info("[admin-demo] Triggering no-show processing (offset=%s min)", body.dt_offset_minutes)
    with _simulated_time(body.dt_offset_minutes):
        result = _no_show_svc.process_no_shows(db)
    logger.info(
        "[admin-demo] No-show run complete: checked=%d processed=%d",
        result.reservations_checked, result.reservations_processed,
    )
    return result


@router.post(
    "/process-offers",
    response_model=ProcessOffersResponse,
    summary="[DEMO] Send waitlist offers for released slots",
    description=(
        "Scans all released reservations and issues a claim offer to the first "
        "eligible waiting student for each slot (FCFS).  Idempotent: slots that "
        "already have a live offer are skipped.  Pass dt_offset_minutes to shift "
        "the clock used for offer-expiry calculations."
    ),
)
def demo_process_offers(
    body: OffsetBody = OffsetBody(),
    db: Session = Depends(get_db),
    _: None = Depends(_require_demo_access),
) -> ProcessOffersResponse:
    logger.info("[admin-demo] Triggering process-offers (offset=%s min)", body.dt_offset_minutes)
    with _simulated_time(body.dt_offset_minutes):
        result = _waitlist_svc.process_offers(db)
    logger.info(
        "[admin-demo] process-offers complete: released_checked=%d offers_generated=%d",
        result.released_reservations_checked, result.offers_generated,
    )
    return result


@router.post(
    "/process-expirations",
    response_model=ProcessExpirationsResponse,
    summary="[DEMO] Expire timed-out waitlist offers and advance the queue",
    description=(
        "Finds all 'offered' waitlist entries whose 5-minute window has closed, "
        "marks them expired, and issues a new offer to the next waiting student. "
        "Use dt_offset_minutes to jump the clock past the 5-minute expiry window "
        "without waiting (e.g. dt_offset_minutes=6)."
    ),
)
def demo_process_expirations(
    body: OffsetBody = OffsetBody(),
    db: Session = Depends(get_db),
    _: None = Depends(_require_demo_access),
) -> ProcessExpirationsResponse:
    logger.info("[admin-demo] Triggering process-expirations (offset=%s min)", body.dt_offset_minutes)
    with _simulated_time(body.dt_offset_minutes):
        result = _waitlist_svc.process_expirations(db)
    logger.info(
        "[admin-demo] process-expirations complete: expired=%d new_offers=%d",
        result.entries_expired, result.new_offers_generated,
    )
    return result


@router.post(
    "/send-reminders",
    response_model=ReminderSummary,
    summary="[DEMO] Send upcoming-reservation reminders",
    description=(
        "Generates reminder notifications + mock emails for students with reserved "
        "slots starting within window_minutes.  Pass dt_offset_minutes to shift "
        "the reference clock.  Skips slots where a reminder was already sent."
    ),
)
def demo_send_reminders(
    body: ReminderDemoBody = ReminderDemoBody(),
    db: Session = Depends(get_db),
    _: None = Depends(_require_demo_access),
) -> ReminderSummary:
    logger.info(
        "[admin-demo] Triggering send-reminders (window=%d min, offset=%s min)",
        body.window_minutes, body.dt_offset_minutes,
    )
    with _simulated_time(body.dt_offset_minutes):
        # Re-use the existing endpoint logic directly (it shares the same db session).
        result = _send_reminders_endpoint(window_minutes=body.window_minutes, db=db)
    logger.info(
        "[admin-demo] send-reminders complete: sent=%d skipped_dup=%d",
        result.reminders_sent, result.skipped_already_sent,
    )
    return result


@router.post(
    "/claim-waitlist",
    response_model=ClaimResponse,
    summary="[DEMO] Claim a waitlist offer (convenience wrapper)",
    description=(
        "Exercises the full claim path for demos.  Provide a user_id, "
        "waitlist_entry_id, and coordinates.  Use ASU building coordinates "
        "(Library: 33.4149,-111.8945  SDFC: 33.4188,-111.9318) to pass the "
        "geofence, or use distant coords to demo a geofence failure.  "
        "dt_offset_minutes shifts the offer-expiry check."
    ),
)
def demo_claim_waitlist(
    body: ClaimDemoBody,
    db: Session = Depends(get_db),
    _: None = Depends(_require_demo_access),
) -> ClaimResponse:
    from app.schemas.waitlist_process import ClaimRequest  # local import avoids circular
    logger.info(
        "[admin-demo] Claim attempt: user=%d waitlist_entry=%d offset=%s min",
        body.user_id, body.waitlist_entry_id, body.dt_offset_minutes,
    )
    claim_req = ClaimRequest(
        user_id=body.user_id,
        waitlist_entry_id=body.waitlist_entry_id,
        submitted_latitude=body.submitted_latitude,
        submitted_longitude=body.submitted_longitude,
    )
    with _simulated_time(body.dt_offset_minutes):
        result = _waitlist_svc.claim_reservation(db, claim_req)
    logger.info("[admin-demo] Claim result: success=%s result=%s", result.success, result.result)
    return result


@router.get(
    "/inspect",
    response_model=InspectSnapshot,
    summary="[DEMO] Read-only DB snapshot for quick visual verification",
    description=(
        "Returns a compact snapshot of the current database state: "
        "recent/released reservations, waitlist queue, notifications, and "
        "check-in logs.  Read-only — no data is mutated."
    ),
)
def demo_inspect(
    db: Session = Depends(get_db),
    _: None = Depends(_require_demo_access),
) -> InspectSnapshot:
    recent_reservations = (
        db.query(Reservation)
        .order_by(Reservation.created_at.desc())
        .limit(20)
        .all()
    )
    released_reservations = (
        db.query(Reservation)
        .filter(Reservation.status == ReservationStatus.released)
        .order_by(Reservation.created_at.desc())
        .limit(20)
        .all()
    )
    recent_waitlist = (
        db.query(WaitlistEntry)
        .order_by(WaitlistEntry.created_at.asc())
        .limit(50)
        .all()
    )
    recent_notifications = (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    recent_check_in_logs = (
        db.query(CheckInLog)
        .order_by(CheckInLog.created_at.desc())
        .limit(50)
        .all()
    )

    return InspectSnapshot(
        recent_reservations=[ReservationResponse.model_validate(r) for r in recent_reservations],
        released_reservations=[ReservationResponse.model_validate(r) for r in released_reservations],
        recent_waitlist=[WaitlistResponse.model_validate(e) for e in recent_waitlist],
        recent_notifications=[NotificationResponse.model_validate(n) for n in recent_notifications],
        recent_check_in_logs=[CheckInLogOut.model_validate(l) for l in recent_check_in_logs],
    )
