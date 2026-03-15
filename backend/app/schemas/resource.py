from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.resource import ResourceType
from app.schemas.building import BuildingSummary


class ResourceSummary(BaseModel):
    """Minimal resource info embedded in reservation/waitlist responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    resource_type: ResourceType
    building: BuildingSummary


class ResourceResponse(BaseModel):
    """Full resource detail used on browse/availability pages."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    building: BuildingSummary
    resource_type: ResourceType
    name: str
    capacity: int
    features: str | None
    is_active: bool
    created_at: datetime
