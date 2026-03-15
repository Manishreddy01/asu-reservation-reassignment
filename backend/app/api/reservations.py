from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services.reservation_service import create_reservation

router = APIRouter(prefix="/reservations", tags=["Reservations"])


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
