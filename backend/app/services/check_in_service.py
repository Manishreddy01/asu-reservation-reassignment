"""
Check-in service.

Validates a student's geolocation against the building geofence,
verifies the time window, updates reservation status on success,
and always writes a CheckInLog record.
"""

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.check_in_log import CheckInLog
from app.models.reservation import Reservation, ReservationStatus
from app.models.resource import Resource
from app.schemas.check_in import CheckInRequest, CheckInResponse
from app.services.geofence import check_geofence

# Statuses that allow a check-in attempt
_CHECKABLE = {ReservationStatus.reserved, ReservationStatus.reassigned}


def process_check_in(db: Session, data: CheckInRequest) -> CheckInResponse:
    """
    Validate and process a student check-in attempt.

    Steps:
      1. Verify reservation exists and belongs to the requesting user.
      2. Verify the reservation is in a checkable status.
      3. Resolve the associated resource and building.
      4. Compute Haversine distance; evaluate geofence.
      5. Evaluate check-in time window.
      6. Determine result and (on success) update reservation.
      7. Write CheckInLog record.
      8. Return structured response.
    """

    # ── 1. Reservation lookup ───────────────────────────────────────────────
    reservation = (
        db.query(Reservation)
        .filter(Reservation.id == data.reservation_id)
        .first()
    )
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation {data.reservation_id} not found.",
        )

    if reservation.user_id != data.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This reservation does not belong to you.",
        )

    # ── 2. Status guard ─────────────────────────────────────────────────────
    if reservation.status == ReservationStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already checked in for this reservation.",
        )
    if reservation.status not in _CHECKABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Check-in is not available for a reservation with "
                f"status '{reservation.status.value}'."
            ),
        )

    # ── 3. Resource and building lookup ─────────────────────────────────────
    resource = db.query(Resource).filter(Resource.id == reservation.resource_id).first()
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

    # ── 4. Geofence evaluation ──────────────────────────────────────────────
    distance_meters, within_geofence = check_geofence(
        submitted_lat=data.submitted_latitude,
        submitted_lon=data.submitted_longitude,
        building_lat=building.latitude,
        building_lon=building.longitude,
        radius_meters=building.geofence_radius_meters,
    )

    # ── 5. Time-window evaluation ───────────────────────────────────────────
    # check_in_deadline = start_time + 15 min  (stored on reservation)
    # window_open       = start_time - 15 min  = deadline - 30 min
    # window_close      = check_in_deadline
    now = dt.datetime.now(tz=dt.timezone.utc)
    window_open = reservation.check_in_deadline - dt.timedelta(minutes=30)
    window_close = reservation.check_in_deadline
    within_time_window = window_open <= now <= window_close

    # ── 6. Determine result ─────────────────────────────────────────────────
    # Time window takes precedence in the result label; geofence is secondary.
    if within_geofence and within_time_window:
        result = "success"
    elif not within_time_window:
        result = "outside_time_window"
    else:
        result = "outside_geofence"

    # ── 7. Update reservation on success ────────────────────────────────────
    if result == "success":
        reservation.status = ReservationStatus.active
        reservation.checked_in_at = now
        db.add(reservation)

    # ── 8. Write CheckInLog ─────────────────────────────────────────────────
    log = CheckInLog(
        reservation_id=reservation.id,
        user_id=data.user_id,
        submitted_latitude=data.submitted_latitude,
        submitted_longitude=data.submitted_longitude,
        distance_to_building_meters=distance_meters,
        was_within_geofence=within_geofence,
        was_within_time_window=within_time_window,
        result=result,
    )
    db.add(log)
    db.commit()
    db.refresh(reservation)

    # ── 9. Build response ───────────────────────────────────────────────────
    message = _build_message(result, distance_meters, building.geofence_radius_meters)

    return CheckInResponse(
        reservation_id=reservation.id,
        user_id=data.user_id,
        distance_meters=distance_meters,
        geofence_radius_meters=building.geofence_radius_meters,
        within_geofence=within_geofence,
        within_time_window=within_time_window,
        reservation_status=reservation.status.value,
        result=result,
        message=message,
    )


def _build_message(result: str, distance: float, radius: float) -> str:
    if result == "success":
        return f"Check-in successful. You are {distance:.1f} m from the building."
    if result == "outside_geofence":
        return (
            f"Check-in failed: you are {distance:.1f} m from the building "
            f"(allowed radius: {radius:.0f} m). Please move closer and try again."
        )
    if result == "outside_time_window":
        return (
            "Check-in failed: you are outside the check-in window. "
            "The window opens 15 minutes before your reservation and closes "
            "15 minutes after the start time."
        )
    return "Check-in could not be completed."
