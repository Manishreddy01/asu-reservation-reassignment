"""
No-show API router.

POST /no-shows/process
  Runs no-show detection and releases expired unattended reservations.
  Safe to call multiple times — already-released reservations are ignored.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.no_show import NoShowProcessResponse
from app.services.no_show_service import process_no_shows

router = APIRouter(prefix="/no-shows", tags=["no-shows"])


@router.post("/process", response_model=NoShowProcessResponse)
def run_no_show_processing(db: Session = Depends(get_db)) -> NoShowProcessResponse:
    """
    Detect and release all reservations whose check-in deadline has passed
    without a successful check-in.

    - Eligible: status=reserved, check_in_deadline in the past, checked_in_at null.
    - Each eligible reservation is transitioned to status=released.
    - Each affected student receives an in-app notification and a mock email.
    - Idempotent: calling this endpoint multiple times will not re-process
      already-released reservations or duplicate notifications.
    """
    return process_no_shows(db)
