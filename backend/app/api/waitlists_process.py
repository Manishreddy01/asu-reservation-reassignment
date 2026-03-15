"""
Block 12 — Waitlist offer, expiration, and claim endpoints.

Endpoints:
  POST /api/v1/waitlists/process-offers
      Scans all released reservations and issues a claim offer to the first
      eligible waiting student for each slot.

  POST /api/v1/waitlists/process-expirations
      Finds all offered entries whose window has closed, marks them expired,
      and advances the queue to the next waiting student where applicable.

  POST /api/v1/waitlists/claim
      Validates a student's claim attempt (geofence check), then reassigns
      the reservation to the claiming student on success.

All three endpoints are prototype-friendly (no auth required for process-*
batch endpoints; claim uses user_id from the request body to match the
mock-auth pattern used across this project).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.waitlist_process import (
    ClaimRequest,
    ClaimResponse,
    ProcessExpirationsResponse,
    ProcessOffersResponse,
)
from app.services import waitlist_service

router = APIRouter(prefix="/waitlists", tags=["Waitlist Processing"])


@router.post(
    "/process-offers",
    response_model=ProcessOffersResponse,
    summary="Generate waitlist offers",
    description=(
        "Scans all released reservations and sends a 5-minute claim offer "
        "to the first eligible waiting student (FCFS). "
        "Skips slots that already have a live non-expired offer. "
        "Safe to call multiple times — idempotent."
    ),
)
def process_offers(db: Session = Depends(get_db)) -> ProcessOffersResponse:
    return waitlist_service.process_offers(db)


@router.post(
    "/process-expirations",
    response_model=ProcessExpirationsResponse,
    summary="Process expired waitlist offers",
    description=(
        "Finds all offered waitlist entries whose 5-minute window has closed. "
        "Marks them expired and advances the queue to the next waiting student "
        "for each slot that is still released."
    ),
)
def process_expirations(db: Session = Depends(get_db)) -> ProcessExpirationsResponse:
    return waitlist_service.process_expirations(db)


@router.post(
    "/claim",
    response_model=ClaimResponse,
    summary="Claim a waitlist slot",
    description=(
        "Validates a student's claim attempt against the building geofence. "
        "On success, reassigns the released reservation to the claiming student "
        "and marks their waitlist entry as claimed. "
        "Returns a clear failure response if outside the geofence, if the offer "
        "has expired, or if the slot is no longer available."
    ),
)
def claim(body: ClaimRequest, db: Session = Depends(get_db)) -> ClaimResponse:
    return waitlist_service.claim_reservation(db, body)
