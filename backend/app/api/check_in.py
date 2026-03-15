"""
Check-in API router.

POST /check-in
  Accepts student coordinates and validates them against the building geofence
  and the reservation's check-in time window.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.check_in import CheckInRequest, CheckInResponse
from app.services.check_in_service import process_check_in

router = APIRouter(prefix="/check-in", tags=["check-in"])


@router.post("", response_model=CheckInResponse)
def check_in(payload: CheckInRequest, db: Session = Depends(get_db)) -> CheckInResponse:
    """
    Validate a student's check-in attempt.

    - Verifies the reservation exists and belongs to the user.
    - Computes Haversine distance from submitted coordinates to the building.
    - Validates the check-in time window (start - 15 min → start + 15 min).
    - Activates the reservation and records a CheckInLog on success.
    - Always records a CheckInLog even on failure.
    """
    return process_check_in(db, payload)
