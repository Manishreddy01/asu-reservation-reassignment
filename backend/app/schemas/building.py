from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BuildingSummary(BaseModel):
    """Minimal building info embedded in other responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    geofence_radius_meters: float


class BuildingResponse(BuildingSummary):
    """Full building detail, including placeholder geofence coordinates."""
    latitude: float
    longitude: float
    created_at: datetime
