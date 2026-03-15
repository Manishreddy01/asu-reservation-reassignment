from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.resource import Resource, ResourceType
from app.schemas.resource import ResourceResponse

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get(
    "",
    response_model=list[ResourceResponse],
    summary="List resources",
    description=(
        "Returns bookable resources (study rooms and recreation courts). "
        "Filter by building_id or resource_type as needed."
    ),
)
def list_resources(
    building_id: int | None = Query(None, description="Filter by building ID"),
    resource_type: ResourceType | None = Query(None, description="Filter by type: study_room or recreation_court"),
    db: Session = Depends(get_db),
) -> list[Resource]:
    q = db.query(Resource).filter(Resource.is_active.is_(True))
    if building_id is not None:
        q = q.filter(Resource.building_id == building_id)
    if resource_type is not None:
        q = q.filter(Resource.resource_type == resource_type)
    return q.order_by(Resource.name).all()


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
    summary="Get resource detail",
)
def get_resource(resource_id: int, db: Session = Depends(get_db)) -> Resource:
    resource = (
        db.query(Resource)
        .filter(Resource.id == resource_id, Resource.is_active.is_(True))
        .first()
    )
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_id} not found.",
        )
    return resource
