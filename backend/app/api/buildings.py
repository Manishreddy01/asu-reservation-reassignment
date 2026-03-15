from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.building import Building
from app.schemas.building import BuildingResponse

router = APIRouter(prefix="/buildings", tags=["Buildings"])


@router.get(
    "",
    response_model=list[BuildingResponse],
    summary="List all buildings",
    description="Returns all campus buildings with their geofence coordinates.",
)
def list_buildings(db: Session = Depends(get_db)) -> list[Building]:
    return db.query(Building).order_by(Building.name).all()
