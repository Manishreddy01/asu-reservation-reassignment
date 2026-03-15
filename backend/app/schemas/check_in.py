"""
Check-in request and response schemas.
"""

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    user_id: int
    reservation_id: int
    submitted_latitude: float = Field(..., ge=-90.0, le=90.0)
    submitted_longitude: float = Field(..., ge=-180.0, le=180.0)


class CheckInResponse(BaseModel):
    reservation_id: int
    user_id: int
    distance_meters: float
    geofence_radius_meters: float
    within_geofence: bool
    within_time_window: bool
    reservation_status: str
    result: str
    message: str
