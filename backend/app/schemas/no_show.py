"""
No-show processing response schemas.
"""

import datetime
from pydantic import BaseModel


class NoShowResult(BaseModel):
    """Summary record for one reservation processed by the no-show job."""
    reservation_id: int
    user_id: int
    resource_name: str
    reservation_date: datetime.date
    start_time: datetime.time


class NoShowProcessResponse(BaseModel):
    """Response returned by POST /api/v1/no-shows/process."""
    reservations_checked: int
    reservations_processed: int
    processed: list[NoShowResult]
